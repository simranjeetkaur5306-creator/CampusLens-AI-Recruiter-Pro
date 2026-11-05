from rest_framework.test import APITestCase

from candidates.models import Candidate
from recruiters.models import Recruiter

from .models import User

PASSWORD = "StrongPass#2026"
CANDIDATE_URL = "/api/candidates/me/"
RECRUITER_URL = "/api/recruiters/me/"


class ProfileTests(APITestCase):
    def register(self, role, email):
        return self.client.post(
            f"/api/auth/register/{role}/",
            {
                "email": email,
                "first_name": "Test",
                "last_name": "User",
                "password": PASSWORD,
                "password2": PASSWORD,
            },
            format="json",
        )

    def login(self, email):
        res = self.client.post(
            "/api/auth/login/", {"email": email, "password": PASSWORD}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def login_as(self, role, email=None):
        email = email or f"{role}@example.com"
        self.client.credentials()  # clear any previous login
        self.register(role, email)
        self.login(email)
        return email

    def test_registration_creates_candidate_profile(self):
        self.register("candidate", "c@example.com")
        user = User.objects.get(email="c@example.com")
        self.assertTrue(Candidate.objects.filter(user=user).exists())
        self.assertFalse(Recruiter.objects.filter(user=user).exists())

    def test_registration_creates_recruiter_profile(self):
        self.register("recruiter", "r@example.com")
        user = User.objects.get(email="r@example.com")
        self.assertTrue(Recruiter.objects.filter(user=user).exists())
        self.assertFalse(Candidate.objects.filter(user=user).exists())

    def test_candidate_get_profile(self):
        self.login_as("candidate")
        res = self.client.get(CANDIDATE_URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["email"], "candidate@example.com")
        self.assertEqual(res.data["headline"], "")

    def test_candidate_patch_profile(self):
        self.login_as("candidate")
        res = self.client.patch(
            CANDIDATE_URL,
            {
                "phone": "+91 98765 43210",
                "headline": "ML student",
                "graduation_year": 2027,
                "github_url": "https://github.com/example",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["headline"], "ML student")
        self.assertEqual(self.client.get(CANDIDATE_URL).data["graduation_year"], 2027)

    def test_candidate_patch_rejects_readonly_fields(self):
        self.login_as("candidate")
        res = self.client.patch(CANDIDATE_URL, {"email": "x@x.com", "id": 99}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.data["errors"])
        self.assertIn("id", res.data["errors"])

    def test_candidate_patch_invalid_values(self):
        self.login_as("candidate")
        res = self.client.patch(
            CANDIDATE_URL,
            {"graduation_year": 1800, "phone": "abc", "github_url": "notaurl"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        for key in ("graduation_year", "phone", "github_url"):
            self.assertIn(key, res.data["errors"])

    def test_recruiter_get_and_patch(self):
        self.login_as("recruiter")
        self.assertEqual(self.client.get(RECRUITER_URL).status_code, 200)
        res = self.client.patch(
            RECRUITER_URL,
            {
                "company_name": "Acme Tech",
                "designation": "HR Manager",
                "company_website": "https://acme.example.com",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["company_name"], "Acme Tech")

    def test_recruiter_patch_rejects_readonly_and_unknown_fields(self):
        self.login_as("recruiter")
        res = self.client.patch(RECRUITER_URL, {"email": "x@x.com", "salary": 1}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.data["errors"])
        self.assertIn("salary", res.data["errors"])

    def test_candidate_cannot_access_recruiter_endpoint(self):
        self.login_as("candidate")
        self.assertEqual(self.client.get(RECRUITER_URL).status_code, 403)
        self.assertEqual(
            self.client.patch(RECRUITER_URL, {"company_name": "X"}, format="json").status_code,
            403,
        )

    def test_recruiter_cannot_access_candidate_endpoint(self):
        self.login_as("recruiter")
        self.assertEqual(self.client.get(CANDIDATE_URL).status_code, 403)
        self.assertEqual(
            self.client.patch(CANDIDATE_URL, {"headline": "X"}, format="json").status_code,
            403,
        )

    def test_unauthenticated_requests_get_401(self):
        self.assertEqual(self.client.get(CANDIDATE_URL).status_code, 401)
        self.assertEqual(self.client.get(RECRUITER_URL).status_code, 401)

    def test_profile_created_on_first_access_for_existing_user(self):
        user = User.objects.create_user(
            username="old@example.com",
            email="old@example.com",
            password=PASSWORD,
            role="candidate",
        )
        self.assertFalse(Candidate.objects.filter(user=user).exists())
        self.login("old@example.com")
        self.assertEqual(self.client.get(CANDIDATE_URL).status_code, 200)
        self.assertTrue(Candidate.objects.filter(user=user).exists())

    def test_profiles_are_isolated_between_users(self):
        self.login_as("candidate", "a@example.com")
        self.client.patch(CANDIDATE_URL, {"headline": "Only A"}, format="json")
        self.login_as("candidate", "b@example.com")
        self.assertEqual(self.client.get(CANDIDATE_URL).data["headline"], "")