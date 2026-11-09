import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase
from unittest import mock

from accounts.models import User
from jobs.models import Job
from resumes.models import Resume
from resumes.test_extraction import SAMPLE_RESUME
from resumes.test_files import make_pdf

from .exceptions import EmbeddingError

PASSWORD = "StrongPass#2026"
DESCRIPTION = "We are looking for a motivated engineer to build and ship AI features with the team."


def job_payload(**extra):
    data = {
        "job_title": "Backend Developer", "company_name": "Acme", "location": "Pune",
        "description": DESCRIPTION, "required_skills": ["Python", "Django"],
    }
    data.update(extra)
    return data


class HookBase(APITestCase):
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
        return User.objects.get(email=email)

    def upload(self, text=SAMPLE_RESUME):
        file = SimpleUploadedFile("cv.pdf", make_pdf(text), content_type="application/pdf")
        return self.client.post("/api/resumes/upload/", {"file": file}, format="multipart")


class ResumeEmbeddingHookTests(HookBase):
    def test_upload_stores_the_resume_vector(self):
        self.login_as("candidate")
        res = self.upload()
        self.assertEqual(res.status_code, 201)
        resume = Resume.objects.get(pk=res.data["resume"]["id"])
        self.assertEqual(len(resume.embedding), 384)
        self.assertTrue(resume.embedding_model)
        self.assertIsNotNone(resume.embedded_at)

    def test_resume_without_readable_text_gets_no_vector(self):
        self.login_as("candidate")
        res = self.upload(text="")
        self.assertEqual(res.data["resume"]["parsing_status"], "failed")
        self.assertIsNone(Resume.objects.get(pk=res.data["resume"]["id"]).embedding)

    def test_upload_succeeds_even_if_embedding_fails(self):
        self.login_as("candidate")
        with mock.patch("matching.services.embeddings.embed_text", side_effect=EmbeddingError("boom")):
            with self.assertLogs("matching.services.storage", level="ERROR"):
                res = self.upload()
        self.assertEqual(res.status_code, 201)
        resume = Resume.objects.get(pk=res.data["resume"]["id"])
        self.assertTrue(resume.is_active)
        self.assertEqual(resume.parsing_status, "success")
        self.assertIsNone(resume.embedding)

    def test_vectors_are_never_sent_to_the_client(self):
        self.login_as("candidate")
        res = self.upload()
        self.assertNotIn("embedding", res.data["resume"])
        self.assertNotIn("embedding_model", res.data["resume"])
        self.assertNotIn("embedding", self.client.get("/api/resumes/me/").data)
        self.assertNotIn("embedding", self.client.get("/api/resumes/").data["results"][0])


class JobEmbeddingHookTests(HookBase):
    def create_job(self, **extra):
        res = self.client.post("/api/jobs/manage/", job_payload(**extra), format="json")
        self.assertEqual(res.status_code, 201, res.data)
        return res.data["id"]

    def test_new_job_gets_a_vector(self):
        self.login_as("recruiter")
        job = Job.objects.get(pk=self.create_job())
        self.assertEqual(len(job.embedding), 384)
        self.assertIsNotNone(job.embedded_at)

    def test_changing_the_description_rebuilds_the_vector(self):
        self.login_as("recruiter")
        jid = self.create_job()
        before = Job.objects.get(pk=jid)
        res = self.client.patch(
            f"/api/jobs/manage/{jid}/",
            {"description": "Lead the kitchen team, plan seasonal menus and manage the food inventory."},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        after = Job.objects.get(pk=jid)
        self.assertGreater(after.embedded_at, before.embedded_at)
        self.assertFalse(np.allclose(before.embedding, after.embedding, atol=1e-6))

    def test_changing_skills_title_experience_or_education_rebuilds_the_vector(self):
        self.login_as("recruiter")
        jid = self.create_job()
        for change in ({"required_skills": ["Docker"]}, {"job_title": "Platform Engineer"},
                       {"required_experience": 4}, {"required_education": "M.Tech"}):
            before = Job.objects.get(pk=jid).embedded_at
            self.assertEqual(self.client.patch(f"/api/jobs/manage/{jid}/", change, format="json").status_code, 200)
            self.assertGreater(Job.objects.get(pk=jid).embedded_at, before, change)

    def test_changes_that_do_not_affect_meaning_keep_the_vector(self):
        self.login_as("recruiter")
        jid = self.create_job()
        before = Job.objects.get(pk=jid).embedded_at
        for change in ({"is_active": False}, {"location": "Delhi"}, {"salary_range": "10 LPA"},
                       {"company_name": "Other Corp"}, {"job_type": "contract"}):
            self.assertEqual(self.client.patch(f"/api/jobs/manage/{jid}/", change, format="json").status_code, 200)
        self.assertEqual(Job.objects.get(pk=jid).embedded_at, before)

    def test_job_is_saved_even_if_embedding_fails(self):
        self.login_as("recruiter")
        with mock.patch("matching.services.embeddings.embed_text", side_effect=EmbeddingError("boom")):
            with self.assertLogs("matching.services.storage", level="ERROR"):
                jid = self.create_job()
        self.assertIsNone(Job.objects.get(pk=jid).embedding)

    def test_failed_update_removes_the_outdated_vector(self):
        self.login_as("recruiter")
        jid = self.create_job()
        self.assertIsNotNone(Job.objects.get(pk=jid).embedding)
        with mock.patch("matching.services.embeddings.embed_text", side_effect=EmbeddingError("boom")):
            with self.assertLogs("matching.services.storage", level="ERROR"):
                res = self.client.patch(f"/api/jobs/manage/{jid}/", {"job_title": "Changed Title"}, format="json")
        self.assertEqual(res.status_code, 200)
        job = Job.objects.get(pk=jid)
        self.assertEqual(job.job_title, "Changed Title")
        self.assertIsNone(job.embedding)

    def test_vectors_are_never_sent_to_the_client(self):
        self.login_as("recruiter")
        jid = self.create_job()
        self.assertNotIn("embedding", self.client.get(f"/api/jobs/manage/{jid}/").data)
        self.login_as("candidate")
        self.assertNotIn("embedding", self.client.get(f"/api/jobs/{jid}/").data)
        self.assertNotIn("embedding", self.client.get("/api/jobs/").data["results"][0])