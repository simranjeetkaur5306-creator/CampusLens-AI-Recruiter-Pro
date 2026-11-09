from unittest import mock

from rest_framework.test import APITestCase

from applications.models import Application
from jobs.models import Job
from recruiters.models import Recruiter
from resumes.models import Resume

from .exceptions import EmbeddingError
from .factories import LoginMixin, make_candidate, make_job, make_resume, set_embedding, vector


class RankingAPITests(LoginMixin, APITestCase):
    def setUp(self):
        owner = self.login_as("recruiter", "owner@example.com")
        self.job = make_job(Recruiter.objects.get(user=owner), title="ML Engineer", skills=("Python", "Machine Learning"))
        set_embedding(self.job, vector(1, 0))
        self.url = f"/api/matching/jobs/{self.job.pk}/ranking/"
        self.n = 0

    def applicant(self, vec, name="Asha", skills=("Python",), status="applied", **profile):
        self.n += 1
        candidate = make_candidate(f"cand{self.n}@example.com")
        user = candidate.user
        user.first_name, user.last_name = name, "Verma"
        user.save()
        for field, value in profile.items():
            setattr(candidate, field, value)
        candidate.save()
        resume = make_resume(candidate, skills=skills)
        if vec is not None:
            set_embedding(resume, vec)
        return Application.objects.create(candidate=candidate, job=self.job, resume=resume, status=status)

    def test_ranked_applicants_with_everything_a_recruiter_needs(self):
        far = self.applicant(vector(0, 1), name="Far")
        best = self.applicant(vector(1, 0.05), name="Best", headline="ML student", university="Kurukshetra University",
                              graduation_year=2027, github_url="https://github.com/best")
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["job"]["job_title"], "ML Engineer")
        self.assertIn("not a hiring decision", res.data["note"])
        self.assertEqual((res.data["applicants_total"], res.data["applicants_scored"]), (2, 2))
        first, second = res.data["results"]
        self.assertEqual((first["rank"], first["application_id"]), (1, best.pk))
        self.assertEqual((second["rank"], second["application_id"]), (2, far.pk))
        self.assertGreater(first["cosine_similarity"], second["cosine_similarity"])
        self.assertTrue(0 <= first["match_percent"] <= 100)
        self.assertEqual(first["candidate"]["name"], "Best Verma")
        self.assertEqual(first["candidate"]["university"], "Kurukshetra University")
        self.assertEqual(first["candidate"]["graduation_year"], 2027)
        self.assertEqual(first["status"], "applied")
        self.assertEqual(first["resume"]["skills"], ["Python"])
        self.assertEqual(first["matching_skills"], ["Python"])
        self.assertEqual(first["missing_skills"], ["Machine Learning"])

    def test_no_resume_text_or_vectors_are_exposed(self):
        self.applicant(vector(1, 0))
        text = str(self.client.get(self.url).data)
        for forbidden in ("embedding", "extracted_text", "Built backend REST APIs"):
            self.assertNotIn(forbidden, text)

    def test_applicants_that_cannot_be_scored_are_listed_last(self):
        scored = self.applicant(vector(1, 0.1), name="Scored")
        unscored = self.applicant(None, name="Unscored")
        res = self.client.get(self.url)
        self.assertEqual((res.data["applicants_total"], res.data["applicants_scored"]), (2, 1))
        rows = res.data["results"]
        self.assertEqual([r["application_id"] for r in rows], [scored.pk, unscored.pk])
        self.assertEqual((rows[1]["rank"], rows[1]["scored"], rows[1]["match_percent"], rows[1]["cosine_similarity"]),
                         (None, False, None, None))

    def test_applicant_whose_resume_was_deleted_is_still_listed(self):
        gone = self.applicant(vector(1, 0))
        Resume.objects.filter(pk=gone.resume_id).delete()
        row = self.client.get(self.url).data["results"][0]
        self.assertIsNone(row["resume"])
        self.assertFalse(row["scored"])

    def test_application_status_is_shown(self):
        self.applicant(vector(1, 0), status="shortlisted")
        self.assertEqual(self.client.get(self.url).data["results"][0]["status"], "shortlisted")

    def test_limit(self):
        for vec in (vector(0, 1), vector(1, 0.1), vector(1, 1)):
            self.applicant(vec)
        res = self.client.get(self.url, {"limit": 2})
        self.assertEqual(len(res.data["results"]), 2)
        self.assertEqual(res.data["applicants_total"], 3)

    def test_invalid_limit(self):
        for bad in ("0", "201", "abc", "-1", "1.5"):
            res = self.client.get(self.url, {"limit": bad})
            self.assertEqual(res.status_code, 400, bad)
            self.assertIn("limit", res.data["errors"])

    def test_no_applicants_gives_an_empty_list(self):
        res = self.client.get(self.url)
        self.assertEqual((res.status_code, res.data["results"], res.data["applicants_total"]), (200, [], 0))

    def test_unpublished_job_can_still_be_ranked(self):
        self.applicant(vector(1, 0))
        Job.objects.filter(pk=self.job.pk).update(is_active=False)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_another_recruiter_cannot_see_the_applicants(self):
        self.applicant(vector(1, 0))
        self.login_as("recruiter", "intruder@example.com")
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_unknown_job(self):
        self.assertEqual(self.client.get("/api/matching/jobs/999999/ranking/").status_code, 404)

    def test_candidates_and_anonymous_users_are_refused(self):
        self.login_as("candidate", "cand@example.com")
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_read_only_endpoint(self):
        self.assertEqual(self.client.post(self.url, {}, format="json").status_code, 405)

    def test_job_without_a_vector_is_embedded_on_the_fly(self):
        self.applicant(vector(1, 0))
        Job.objects.filter(pk=self.job.pk).update(embedding=None, embedded_at=None, embedding_model="")
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertIsNotNone(Job.objects.get(pk=self.job.pk).embedding)

    def test_model_failure_gives_503(self):
        Job.objects.filter(pk=self.job.pk).update(embedding=None, embedded_at=None, embedding_model="")
        with mock.patch("matching.services.embeddings.embed_text", side_effect=EmbeddingError("boom")):
            with self.assertLogs("matching.services.storage", level="ERROR"):
                res = self.client.get(self.url)
        self.assertEqual(res.status_code, 503)
        self.assertIn("message", res.data)

    def test_ranking_does_not_change_anything(self):
        app = self.applicant(vector(1, 0))
        before = (Application.objects.get(pk=app.pk).updated_at, Job.objects.get(pk=self.job.pk).embedded_at)
        self.client.get(self.url)
        after = (Application.objects.get(pk=app.pk).updated_at, Job.objects.get(pk=self.job.pk).embedded_at)
        self.assertEqual(before, after)