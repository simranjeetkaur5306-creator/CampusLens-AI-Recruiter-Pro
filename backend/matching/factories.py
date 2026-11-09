"""Small helpers that create test data (used only by the tests)."""
import numpy as np

from accounts.models import User
from candidates.models import Candidate
from jobs.models import Job
from jobs.services import resolve_skills
from recruiters.models import Recruiter
from resumes.models import Resume

DIMENSIONS = 384
RESUME_TEXT = "Built backend REST APIs with Python and Django for a college portal."
JOB_TEXT = "We are looking for a backend developer to build REST APIs with Python and Django."


def make_candidate(email="c@example.com"):
    user = User.objects.create_user(username=email, email=email, password="x", role="candidate")
    return Candidate.objects.create(user=user)


def make_recruiter(email="r@example.com"):
    user = User.objects.create_user(username=email, email=email, password="x", role="recruiter")
    return Recruiter.objects.create(user=user, company_name="Acme")


def make_resume(candidate, text=RESUME_TEXT, skills=("Python", "Django"), active=True, status="success"):
    resume = Resume.objects.create(
        candidate=candidate, file="resumes/1/x.pdf", original_filename="x.pdf", file_type="pdf",
        file_size=1, parsing_status=status, extracted_text=text, is_active=active,
    )
    resume.skills.set(resolve_skills(list(skills)))
    return resume


def make_job(recruiter, title="Backend Developer", description=JOB_TEXT, skills=("Python", "Django"), active=True, **extra):
    job = Job.objects.create(
        recruiter=recruiter, job_title=title, company_name="Acme", location=extra.pop("location", "Pune"),
        description=description, is_active=active, **extra,
    )
    job.required_skills.set(resolve_skills(list(skills)))
    return job


def vector(*head):
    """A unit-length 384-dimensional vector that starts with the given numbers, e.g. vector(1, 1)."""
    values = np.zeros(DIMENSIONS)
    values[: len(head)] = head
    return (values / np.linalg.norm(values)).tolist()


def set_embedding(obj, values):
    type(obj).objects.filter(pk=obj.pk).update(embedding=values)
    obj.refresh_from_db()



PASSWORD = "StrongPass#2026"


class LoginMixin:
    """For APITestCase classes: register a user through the API, log in and keep the token."""

    def login_as(self, role, email=None):
        email = email or f"{role}@example.com"
        self.client.credentials()
        self.client.post(
            f"/api/auth/register/{role}/",
            {"email": email, "first_name": "Test", "last_name": "User", "password": PASSWORD, "password2": PASSWORD},
            format="json",
        )
        token = self.client.post("/api/auth/login/", {"email": email, "password": PASSWORD}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return User.objects.get(email=email)