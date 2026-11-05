from rest_framework.test import APITestCase

from .models import User

PASSWORD = "StrongPass#2026"


def payload(email="alice@example.com", **extra):
    data = {
        "email": email,
        "first_name": "Alice",
        "last_name": "Sharma",
        "password": PASSWORD,
        "password2": PASSWORD,
    }
    data.update(extra)
    return data


class AuthTests(APITestCase):
    def register(self, endpoint="candidate", **kw):
        return self.client.post(f"/api/auth/register/{endpoint}/", payload(**kw), format="json")
    
    def login(self, email="alice@example.com", password=PASSWORD):
        return self.client.post(
            "/api/auth/login/", {"email": email, "password": password}, format="json"
        )

    def auth_as(self, role):
        email = f"{role}@example.com"
        self.register(role, email=email)
        data = self.login(email).data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
        return data

    def test_candidate_registration(self):
        res = self.register("candidate")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["user"]["role"], "candidate")
        user = User.objects.get(email="alice@example.com")
        self.assertNotEqual(user.password, PASSWORD)  # stored hashed
        self.assertTrue(user.check_password(PASSWORD))

    def test_recruiter_registration(self):
        res = self.register("recruiter")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["user"]["role"], "recruiter")

    def test_role_cannot_be_chosen_by_client(self):
        res = self.register("candidate", role="recruiter")
        self.assertEqual(res.data["user"]["role"], "candidate")

    def test_duplicate_email_rejected_case_insensitive(self):
        self.register("candidate")
        res = self.register("recruiter", email="ALICE@example.com")
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.data["errors"])

    def test_password_mismatch(self):
        res = self.register(password2="Different#2026")
        self.assertEqual(res.status_code, 400)
        self.assertIn("password2", res.data["errors"])

    def test_weak_password_rejected(self):
        res = self.register(password="12345678", password2="12345678")
        self.assertEqual(res.status_code, 400)
        self.assertIn("password", res.data["errors"])

    def test_login_returns_tokens_and_role(self):
        self.register("recruiter")
        res = self.login()
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertEqual(res.data["user"]["role"], "recruiter")

    def test_login_wrong_password(self):
        self.register("candidate")
        res = self.login(password="WrongPass#2026")
        self.assertEqual(res.status_code, 401)
        self.assertIn("message", res.data)

    def test_me_requires_authentication(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_me_get_and_update_but_not_role(self):
        self.auth_as("candidate")
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)
        res = self.client.patch(
            "/api/auth/me/", {"first_name": "Asha", "role": "recruiter"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["first_name"], "Asha")
        self.assertEqual(res.data["role"], "candidate")  # role change ignored

    def test_role_based_access(self):
        self.assertEqual(self.client.get("/api/auth/rbac-check/candidate/").status_code, 401)
        self.auth_as("candidate")
        self.assertEqual(self.client.get("/api/auth/rbac-check/candidate/").status_code, 200)
        self.assertEqual(self.client.get("/api/auth/rbac-check/recruiter/").status_code, 403)

    def test_token_refresh(self):
        self.register("candidate")
        refresh = self.login().data["refresh"]
        res = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)

    def test_logout_blacklists_refresh_token(self):
        self.register("candidate")
        refresh = self.login().data["refresh"]
        self.assertEqual(
            self.client.post("/api/auth/logout/", {"refresh": refresh}, format="json").status_code, 200
        )
        res = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(res.status_code, 401)