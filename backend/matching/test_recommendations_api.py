from unittest import mock

from rest_framework.test import APITestCase

from applications.models import Application
from candidates.models import Candidate
from jobs.models import Job
from resumes.models import Resume

from .exceptions import EmbeddingError
from .factories import LoginMixin, make_job, make_recruiter, make_resume, set_embedding, vector
from .services import search

URL = "/api/matching/recommendations/"


class RecommendationsAPITests(LoginMixin, APITestCase):
    def setUp(self):
        recruiter = make_recruiter()
        self.best = make_job(recruiter, title="Best", location="Pune", skills=("Python", "SQL"))
        self.middle = make_job(recruiter, title="Middle", location="Delhi", skills=("Docker",))
        self.weak = make_job(recruiter, title="Weak", location="Pune", skills=("Cooking",))
        self.closed = make_job(recruiter, title="Closed", active=False, skills=("Python",))
        self.no_vector = make_job(recruiter, title="No vector", skills=("Python",))
        for job, vec in ((self.best, vector(1, 0.05)), (self.middle, vector(1, 1)),
                         (self.weak, vector(0, 1)), (self.closed, vector(1, 0))):
            set_embedding(job, vec)
        user = self.login_as("candidate", "cand@example.com")
        self.candidate = Candidate.objects.get(user=user)
        self.resume = make_resume(self.candidate, skills=("Python", "Docker"))
        set_embedding(self.resume, vector(1, 0))

    def titles(self, **params):
        res = self.client.get(URL, params)
        self.assertEqual(res.status_code, 200, res.data)
        return [row["job"]["job_title"] for row in res.data["results"]]

    def test_jobs_ranked_best_first_with_scores_and_skills(self):
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["resume"]["id"], self.resume.pk)
        self.assertEqual([r["job"]["job_title"] for r in res.data["results"]], ["Best", "Middle", "Weak"])
        first = res.data["results"][0]
        self.assertTrue(0 <= first["match_percent"] <= 100)
        self.assertEqual(first["matching_skills"], ["Python"])
        self.assertEqual(first["missing_skills"], ["SQL"])
        self.assertFalse(first["already_applied"])
        self.assertGreater(first["cosine_similarity"], res.data["results"][1]["cosine_similarity"])

    def test_closed_jobs_and_jobs_without_a_vector_are_not_recommended(self):
        titles = self.titles()
        self.assertNotIn("Closed", titles)
        self.assertNotIn("No vector", titles)

    def test_no_vectors_in_the_response(self):
        self.assertNotIn("embedding", str(self.client.get(URL).data))

    def test_same_order_as_the_search_service(self):
        expected = [r.item.job_title for r in search.search_jobs_for_resume(self.resume)]
        self.assertEqual(self.titles(), expected)

    def test_applied_jobs_disappear_unless_requested(self):
        self.assertEqual(self.client.post("/api/applications/", {"job": self.best.pk}, format="json").status_code, 201)
        self.assertEqual(self.titles(), ["Middle", "Weak"])
        res = self.client.get(URL, {"include_applied": "true"})
        self.assertEqual([(r["job"]["job_title"], r["already_applied"]) for r in res.data["results"]],
                         [("Best", True), ("Middle", False), ("Weak", False)])

    def test_filters_limit_and_min_percent(self):
        self.assertEqual(self.titles(location="pune"), ["Best", "Weak"])
        self.assertEqual(self.titles(skills="docker"), ["Middle"])  # only Middle requires Docker
        self.assertEqual(self.titles(limit=1), ["Best"])
        self.assertEqual(self.titles(min_percent=50), ["Best", "Middle"])
        self.assertEqual(self.titles(min_percent=100), [])

    def test_only_the_active_resume_counts(self):
        Resume.objects.filter(pk=self.resume.pk).update(is_active=False)
        newer = make_resume(self.candidate, skills=("Cooking",))
        set_embedding(newer, vector(0, 1))  # now the candidate looks like the cook
        self.assertEqual(self.titles()[0], "Weak")

    def test_resume_is_required(self):
        Resume.objects.all().delete()
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 400)
        self.assertIn("resume", res.data["errors"])

    def test_failed_or_inactive_resumes_do_not_count(self):
        Resume.objects.all().update(is_active=False)
        make_resume(self.candidate, status="failed", active=True)
        self.assertEqual(self.client.get(URL).status_code, 400)

    def test_resume_without_a_vector_is_embedded_on_the_fly(self):
        Resume.objects.filter(pk=self.resume.pk).update(embedding=None, embedded_at=None, embedding_model="")
        self.assertEqual(self.client.get(URL).status_code, 200)
        self.assertIsNotNone(Resume.objects.get(pk=self.resume.pk).embedding)

    def test_model_failure_gives_503(self):
        Resume.objects.filter(pk=self.resume.pk).update(embedding=None, embedded_at=None, embedding_model="")
        with mock.patch("matching.services.embeddings.embed_text", side_effect=EmbeddingError("boom")):
            with self.assertLogs("matching.services.storage", level="ERROR"):
                res = self.client.get(URL)
        self.assertEqual(res.status_code, 503)

    def test_only_candidates_can_use_it(self):
        self.login_as("recruiter", "rec@example.com")
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_invalid_parameters(self):
        bad = [{"limit": "0"}, {"limit": "51"}, {"limit": "abc"}, {"min_percent": "-1"}, {"min_percent": "101"},
               {"min_percent": "abc"}, {"min_percent": "nan"}, {"include_applied": "maybe"}, {"ordering": "job_title"},
               {"job_type": "weekend"}]
        for params in bad:
            res = self.client.get(URL, params)
            self.assertEqual(res.status_code, 400, params)
            self.assertIn("errors", res.data)

    def test_read_only(self):
        self.assertEqual(self.client.post(URL, {}, format="json").status_code, 405)
        self.assertEqual(Application.objects.count(), 0)