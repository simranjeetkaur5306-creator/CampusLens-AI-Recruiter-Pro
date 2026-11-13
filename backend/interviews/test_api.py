from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from applications.models import Application
from candidates.models import Candidate
from core.llm_fakes import FakeGeminiClient, gemini_error
from interviews.models import InterviewQuestionSet
from matching.factories import LoginMixin, make_candidate, make_job, make_recruiter, make_resume
from recruiters.models import Recruiter

REPLY = {
    "technical": [
        {"question": "How does Django's ORM build a query?", "skill": "Django", "difficulty": "medium", "answer_guide": "QuerySets are lazy."},
        {"question": "What are Python decorators used for?", "skill": "Python", "difficulty": "easy", "answer_guide": "Wrapping functions."},
    ],
    "conceptual": [{"question": "What is the difference between REST and RPC?", "skill": None, "difficulty": "medium", "answer_guide": "Resources vs actions."}],
    "project_based": [{"question": "Why did you choose PostgreSQL for your college portal?", "skill": "PostgreSQL", "difficulty": "medium", "answer_guide": "Trade-offs."}],
    "hr": [{"question": "Tell me about a time you missed a deadline.", "skill": None, "difficulty": "easy", "answer_guide": "Honest and reflective."}],
}

JOB_URL = "/api/interviews/jobs/{}/questions/"
APP_URL = "/api/interviews/applications/{}/questions/"
LIST_URL = "/api/interviews/questions/"


@override_settings(GEMINI_API_KEY="test-key", GEMINI_MODEL="test-model")
class InterviewQuestionsAPITests(LoginMixin, APITestCase):
    def setUp(self):
        cache.clear()  # throttle counters
        self.recruiter_user = self.login_as("recruiter", "rec@example.com")
        self.recruiter = Recruiter.objects.get(user=self.recruiter_user)
        self.job = make_job(self.recruiter, title="Backend Developer", skills=("Python", "Django"))
        self.closed_job = make_job(self.recruiter, title="Closed Role", active=False)

        self.candidate_user = self.login_as("candidate", "cand@example.com")
        self.candidate = Candidate.objects.get(user=self.candidate_user)
        self.resume = make_resume(self.candidate, skills=("Python", "PostgreSQL"))
        self.resume.contact = {"name": "Test User", "email": "cand@example.com", "phone": "9876543210"}
        self.resume.projects = [{"title": "College Portal", "technologies": ["Python", "PostgreSQL"], "description": ["REST APIs"]}]
        self.resume.save()
        self.client_fake = FakeGeminiClient(reply=REPLY)

    def post(self, url):
        with mock.patch("core.llm.get_client", return_value=self.client_fake):
            return self.client.post(url, {}, format="json")

    # ---------- candidate ----------
    def test_candidate_gets_saved_practice_questions(self):
        res = self.post(JOB_URL.format(self.job.pk))
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["audience"], "candidate")
        self.assertEqual(res.data["job"]["job_title"], "Backend Developer")
        self.assertEqual(res.data["question_count"], 5)
        self.assertTrue(res.data["used_resume"])
        self.assertEqual(res.data["questions"]["technical"][0]["skill"], "Django")
        self.assertEqual(res.data["questions"]["project_based"][0]["skill"], "PostgreSQL")  # from the resume
        self.assertEqual(list(res.data["categories"]), ["technical", "conceptual", "project_based", "hr"])
        self.assertIn("not a test result", res.data["note"])

        saved = InterviewQuestionSet.objects.get()
        self.assertEqual((saved.model_name, saved.prompt_tokens, saved.completion_tokens), ("fake-model", 120, 340))
        self.assertEqual(saved.resume, self.resume)

        sent = self.client_fake.sent_text()
        self.assertIn("College Portal", sent)
        self.assertIn("Backend Developer", sent)
        for private in ("cand@example.com", "9876543210"):
            self.assertNotIn(private, sent)

    def test_candidate_needs_a_parsed_active_resume(self):
        self.resume.is_active = False
        self.resume.save()
        res = self.post(JOB_URL.format(self.job.pk))
        self.assertEqual(res.status_code, 400)
        self.assertIn("resume", res.data["errors"])
        self.assertEqual(self.client_fake.calls, [])

    def test_closed_job_only_if_already_applied(self):
        self.assertEqual(self.post(JOB_URL.format(self.closed_job.pk)).status_code, 404)
        Application.objects.create(candidate=self.candidate, job=self.closed_job, resume=self.resume)
        self.assertEqual(self.post(JOB_URL.format(self.closed_job.pk)).status_code, 201)

    def test_missing_job_and_recruiter_cannot_use_candidate_endpoint(self):
        self.assertEqual(self.post(JOB_URL.format(99999)).status_code, 404)
        self.login_as("recruiter", "rec@example.com")
        self.assertEqual(self.post(JOB_URL.format(self.job.pk)).status_code, 403)

    # ---------- recruiter ----------
    def test_recruiter_gets_questions_for_own_applicant(self):
        application = Application.objects.create(candidate=self.candidate, job=self.job, resume=self.resume)
        self.login_as("recruiter", "rec@example.com")
        res = self.post(APP_URL.format(application.pk))
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["audience"], "recruiter")
        self.assertEqual(res.data["application"], application.pk)
        self.assertEqual(res.data["candidate_name"], "Test User")
        self.assertIn("A recruiter will use these questions", self.client_fake.sent_text())

    def test_recruiter_cannot_use_another_recruiters_application(self):
        other_job = make_job(make_recruiter("other@example.com"))
        application = Application.objects.create(candidate=self.candidate, job=other_job, resume=self.resume)
        self.login_as("recruiter", "rec@example.com")
        self.assertEqual(self.post(APP_URL.format(application.pk)).status_code, 404)
        self.login_as("candidate", "cand@example.com")
        self.assertEqual(self.post(APP_URL.format(application.pk)).status_code, 403)

    def test_application_whose_resume_was_deleted_gets_job_only_questions(self):
        application = Application.objects.create(candidate=self.candidate, job=self.job, resume=None)
        self.login_as("recruiter", "rec@example.com")
        res = self.post(APP_URL.format(application.pk))
        self.assertEqual(res.status_code, 201)
        self.assertFalse(res.data["used_resume"])
        self.assertIn("CANDIDATE DATA:\nNot available", self.client_fake.sent_text())

    # ---------- failures ----------
    @override_settings(GEMINI_API_KEY="")
    def test_no_api_key_gives_a_clear_503(self):
        res = self.post(JOB_URL.format(self.job.pk))
        self.assertEqual(res.status_code, 503)
        self.assertIn("GEMINI_API_KEY", res.data["message"])
        self.assertEqual(InterviewQuestionSet.objects.count(), 0)

    def test_gemini_rate_limit_gives_429_and_saves_nothing(self):
        self.client_fake = FakeGeminiClient(error=gemini_error(429, "RESOURCE_EXHAUSTED"))
        res = self.post(JOB_URL.format(self.job.pk))
        self.assertEqual(res.status_code, 429)
        self.assertIn("try again", res.data["message"])
        self.assertEqual(InterviewQuestionSet.objects.count(), 0)

    def test_unusable_ai_answer_gives_502(self):
        self.client_fake = FakeGeminiClient(reply={"technical": []})
        self.assertEqual(self.post(JOB_URL.format(self.job.pk)).status_code, 502)

    def test_our_own_rate_limit(self):
        with mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"ai": "2/hour"}):
            codes = [self.post(JOB_URL.format(self.job.pk)).status_code for _ in range(3)]
        self.assertEqual(codes, [201, 201, 429])

    # ---------- saved sets ----------
    def test_list_detail_and_delete_only_your_own_sets(self):
        mine = self.post(JOB_URL.format(self.job.pk)).data["id"]
        other_user = make_candidate("other@example.com").user
        theirs = InterviewQuestionSet.objects.create(
            job=self.job, requested_by=other_user, audience="candidate", questions=REPLY, model_name="m", prompt_version="v1"
        )

        res = self.client.get(LIST_URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual([row["id"] for row in res.data["results"]], [mine])
        self.assertEqual(self.client.get(LIST_URL, {"job": self.closed_job.pk}).data["count"], 0)
        self.assertEqual(self.client.get(LIST_URL, {"job": "abc"}).status_code, 400)

        self.assertEqual(self.client.get(f"{LIST_URL}{mine}/").status_code, 200)
        self.assertEqual(self.client.get(f"{LIST_URL}{theirs.pk}/").status_code, 404)
        self.assertEqual(self.client.delete(f"{LIST_URL}{theirs.pk}/").status_code, 404)
        self.assertEqual(self.client.delete(f"{LIST_URL}{mine}/").status_code, 204)
        self.assertEqual(InterviewQuestionSet.objects.count(), 1)

    def test_login_required(self):
        self.client.credentials()
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)
        self.assertEqual(self.client.post(JOB_URL.format(self.job.pk)).status_code, 401)
