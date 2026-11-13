import json
from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from candidates.models import Candidate
from core.llm import LLMError
from core.llm_fakes import FakeGeminiClient
from matching.factories import LoginMixin, make_job, make_recruiter, make_resume
from skillgap.services import ai_summary, analysis

URL = "/api/skill-gap/jobs/{}/ai-summary/"
REPLY = {
    "summary": "You already have Python, which is the core of this role. Django and Docker are the main gaps.",
    "next_steps": [
        "Build a small Django REST API to learn the framework.",
        "Containerise that API with Docker.",
        "Learn Kubernetes basics.",  # not a gap in the analysis: must be dropped
    ],
}


class CleanSummaryTests(SimpleTestCase):
    def result(self):
        return analysis.analyze(
            resume_skills=["Python"], resume_text="",
            job_skills=[{"name": n, "category": ""} for n in ("Python", "Django", "Docker")],
        )

    def test_steps_must_be_about_real_gaps(self):
        cleaned = ai_summary.clean_summary(REPLY, self.result())
        self.assertEqual(cleaned["summary"], REPLY["summary"])
        self.assertEqual(len(cleaned["next_steps"]), 2)
        self.assertFalse(any("Kubernetes" in step for step in cleaned["next_steps"]))

    def test_missing_summary_is_an_error(self):
        with self.assertRaises(LLMError):
            ai_summary.clean_summary({"summary": "ok"}, self.result())

    def test_prompt_contains_only_analysis_facts(self):
        text = "\n".join(m["content"] for m in ai_summary.build_messages("Backend Developer", self.result()))
        facts = json.loads(text.split("ANALYSIS DATA:\n")[1].split("\n\n")[0])
        self.assertEqual(facts["matched"], ["Python"])
        self.assertEqual(facts["missing"], ["Django", "Docker"])
        self.assertEqual(facts["coverage_percent"], 33.3)


@override_settings(GEMINI_API_KEY="test-key")
class SkillGapAISummaryAPITests(LoginMixin, APITestCase):
    def setUp(self):
        cache.clear()
        self.job = make_job(make_recruiter(), skills=("Python", "Django", "Docker"))
        user = self.login_as("candidate", "cand@example.com")
        self.resume = make_resume(Candidate.objects.get(user=user), skills=("Python",), text="Python developer, cand@example.com")
        self.fake = FakeGeminiClient(reply=REPLY)

    def post(self, job=None):
        with mock.patch("core.llm.get_client", return_value=self.fake):
            return self.client.post(URL.format((job or self.job).pk))

    def test_summary_is_grounded_in_the_analysis(self):
        res = self.post()
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["matched"], ["Python"])
        self.assertEqual(res.data["missing"], ["Django", "Docker"])
        self.assertEqual(res.data["ai_summary"]["summary"], REPLY["summary"])
        self.assertEqual(len(res.data["ai_summary"]["next_steps"]), 2)
        self.assertEqual(res.data["model_name"], "fake-model")
        self.assertNotIn("cand@example.com", self.fake.sent_text())  # resume text is never sent

    def test_job_without_required_skills_needs_no_ai_call(self):
        res = self.post(make_job(self.job.recruiter, title="Open Role", skills=()))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.fake.calls, [])
        self.assertEqual(res.data["ai_summary"]["next_steps"], [])

    @override_settings(GEMINI_API_KEY="")
    def test_no_key_gives_503(self):
        res = self.post()
        self.assertEqual(res.status_code, 503)
        self.assertIn("GEMINI_API_KEY", res.data["message"])

    def test_get_is_not_allowed_and_plain_analysis_still_works(self):
        self.assertEqual(self.client.get(URL.format(self.job.pk)).status_code, 405)
        self.assertEqual(self.client.get(f"/api/skill-gap/jobs/{self.job.pk}/").status_code, 200)
