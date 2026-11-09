from unittest import mock

from rest_framework.test import APITestCase

from accounts.models import User
from jobs.models import Job

from .exceptions import EmbeddingError
from .factories import make_job, make_recruiter
from .services import storage

PASSWORD = "StrongPass#2026"
URL = "/api/matching/jobs/search/"


class JobSearchAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        recruiter = make_recruiter()
        cls.dev = make_job(recruiter, title="Backend Developer", location="Pune", skills=("Python", "Django"),
                           description="Build REST APIs with Python and Django for our hiring platform.")
        cls.chef = make_job(recruiter, title="Restaurant Chef", location="Delhi", skills=("Custom Cooking",),
                            description="Lead the kitchen team, plan menus and manage food inventory.")
        cls.closed = make_job(recruiter, title="Closed Python Developer", active=False, skills=("Python",),
                              description="Build REST APIs with Python and Django, but this job is closed.")
        for job in (cls.dev, cls.chef, cls.closed):
            storage.embed_job(job)

    def login_as(self, role, email=None):
        email = email or f"{role}@example.com"
        self.client.credentials()
        self.client.post(
            f"/api/auth/register/{role}/",
            {"email": email, "first_name": "T", "last_name": "U", "password": PASSWORD, "password2": PASSWORD},
            format="json",
        )
        token = self.client.post("/api/auth/login/", {"email": email, "password": PASSWORD}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_returns_active_jobs_best_match_first(self):
        self.login_as("candidate")
        res = self.client.get(URL, {"q": "python django REST APIs developer"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["query"], "python django REST APIs developer")
        titles = [row["job"]["job_title"] for row in res.data["results"]]
        self.assertEqual(titles, ["Backend Developer", "Restaurant Chef"])  # closed job never shows
        self.assertEqual(res.data["count"], 2)
        first, second = res.data["results"]
        self.assertGreater(first["cosine_similarity"], second["cosine_similarity"])
        self.assertTrue(0 <= first["match_percent"] <= 100)

    def test_result_contains_the_normal_job_fields_but_no_vector(self):
        self.login_as("candidate")
        job = self.client.get(URL, {"q": "python django developer"}).data["results"][0]["job"]
        self.assertEqual(sorted(job["required_skills"]), ["Django", "Python"])
        self.assertNotIn("embedding", job)
        self.assertNotIn("recruiter", job)

    def test_limit(self):
        self.login_as("candidate")
        res = self.client.get(URL, {"q": "python django developer", "limit": 1})
        self.assertEqual(len(res.data["results"]), 1)

    def test_filters_can_be_combined_with_search(self):
        self.login_as("candidate")
        res = self.client.get(URL, {"q": "python django developer", "location": "delhi"})
        self.assertEqual([r["job"]["job_title"] for r in res.data["results"]], ["Restaurant Chef"])
        res = self.client.get(URL, {"q": "python django developer", "skills": "python"})
        self.assertEqual([r["job"]["job_title"] for r in res.data["results"]], ["Backend Developer"])

    def test_jobs_without_a_vector_are_not_returned(self):
        Job.objects.filter(pk=self.chef.pk).update(embedding=None)
        self.login_as("candidate")
        res = self.client.get(URL, {"q": "python django developer"})
        self.assertEqual([r["job"]["job_title"] for r in res.data["results"]], ["Backend Developer"])

    def test_only_candidates_can_search(self):
        self.client.credentials()
        self.assertEqual(self.client.get(URL, {"q": "python developer"}).status_code, 401)
        self.login_as("recruiter")
        self.assertEqual(self.client.get(URL, {"q": "python developer"}).status_code, 403)

    def test_invalid_input_returns_400(self):
        self.login_as("candidate")
        bad_requests = [
            {},                                        # missing q
            {"q": "ab"},                               # too short
            {"q": "x" * 501},                          # too long
            {"q": "!!! ???"},                          # no real words
            {"q": "python developer", "limit": "0"},
            {"q": "python developer", "limit": "51"},
            {"q": "python developer", "limit": "abc"},
            {"q": "python developer", "ordering": "created_at"},
            {"q": "python developer", "job_type": "weekend"},
        ]
        for params in bad_requests:
            res = self.client.get(URL, params)
            self.assertEqual(res.status_code, 400, params)
            self.assertIn("errors", res.data)

    def test_model_failure_gives_503_not_a_crash(self):
        self.login_as("candidate")
        with mock.patch("matching.services.embeddings.embed_text", side_effect=EmbeddingError("boom")):
            res = self.client.get(URL, {"q": "python developer"})
        self.assertEqual(res.status_code, 503)
        self.assertIn("message", res.data)

    def test_other_http_methods_are_not_allowed(self):
        self.login_as("candidate")
        self.assertEqual(self.client.post(URL, {"q": "python developer"}).status_code, 405)

    def test_search_does_not_change_any_job(self):
        self.login_as("candidate")
        before = list(Job.objects.values_list("pk", "embedded_at", "updated_at"))
        self.client.get(URL, {"q": "python developer"})
        self.assertEqual(before, list(Job.objects.values_list("pk", "embedded_at", "updated_at")))