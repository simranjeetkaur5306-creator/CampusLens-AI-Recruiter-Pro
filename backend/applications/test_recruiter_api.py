import tempfile

from django.core.files.base import ContentFile
from django.test import override_settings
from rest_framework.test import APITestCase

from candidates.models import Candidate
from matching.factories import LoginMixin, make_job, make_recruiter, make_resume
from recruiters.models import Recruiter
from resumes.models import Resume

from .models import Application

LIST = "/api/applications/received/"
OWNER = "owner@example.com"


class Base(LoginMixin, APITestCase):
    """One recruiter (owner) with a job and two applicants, plus another recruiter's job."""

    def setUp(self):
        owner_user = self.login_as("recruiter", OWNER)
        self.owner = Recruiter.objects.get(user=owner_user)
        self.job = make_job(self.owner, title="Backend Developer")
        self.other_job = make_job(make_recruiter("other@example.com"), title="Foreign job")
        self.alice = self.apply("alice@example.com", self.job)
        self.bob = self.apply("bob@example.com", self.job)
        self.carol = self.apply("carol@example.com", self.other_job)
        self.as_owner()

    def apply(self, email, job):
        user = self.login_as("candidate", email)
        candidate = Candidate.objects.get(user=user)
        return Application.objects.create(candidate=candidate, job=job, resume=make_resume(candidate))

    def as_owner(self):
        self.login_as("recruiter", OWNER)


class ReceivedListTests(Base):
    def test_lists_only_applications_to_own_jobs(self):
        res = self.client.get(LIST)
        self.assertEqual(res.status_code, 200)
        self.assertEqual({row["id"] for row in res.data["results"]}, {self.alice.pk, self.bob.pk})
        row = next(r for r in res.data["results"] if r["id"] == self.alice.pk)
        self.assertEqual(row["candidate"]["email"], "alice@example.com")
        self.assertEqual(row["job"]["job_title"], "Backend Developer")
        self.assertEqual(sorted(row["resume"]["skills"]), ["Django", "Python"])

    def test_candidates_and_anonymous_users_are_refused(self):
        self.login_as("candidate", "alice@example.com")
        self.assertEqual(self.client.get(LIST).status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get(LIST).status_code, 401)

    def test_filters(self):
        Application.objects.filter(pk=self.bob.pk).update(status="shortlisted")
        shortlisted = self.client.get(LIST, {"status": "shortlisted"})
        self.assertEqual([r["id"] for r in shortlisted.data["results"]], [self.bob.pk])
        by_job = self.client.get(LIST, {"job": self.job.pk})
        self.assertEqual(len(by_job.data["results"]), 2)
        self.assertEqual(len(self.client.get(LIST, {"job": self.other_job.pk}).data["results"]), 0)

    def test_bad_filters_are_rejected(self):
        self.assertEqual(self.client.get(LIST, {"job": "abc"}).status_code, 400)
        self.assertEqual(self.client.get(LIST, {"status": "nope"}).status_code, 400)


class DetailTests(Base):
    def test_detail_has_candidate_and_parsed_resume_but_not_raw_text(self):
        Resume.objects.filter(pk=self.alice.resume_id).update(
            contact={"email": "alice@example.com"},
            education=[{"degree": "B.Tech", "institution": "ACEAR"}],
            experience=[{"title": "Intern", "organization": "Acme", "duration": "2025", "description": ["Built APIs"]}],
        )
        res = self.client.get(f"/api/applications/{self.alice.pk}/")
        self.assertEqual(res.status_code, 200)
        resume = res.data["resume"]
        self.assertEqual(resume["education"][0]["institution"], "ACEAR")
        self.assertEqual(resume["experience"][0]["title"], "Intern")
        self.assertEqual({s["name"] for s in resume["skills"]}, {"Python", "Django"})
        self.assertNotIn("extracted_text", resume)
        self.assertEqual(res.data["candidate"]["name"], "Test User")

    def test_another_recruiters_application_is_404(self):
        self.assertEqual(self.client.get(f"/api/applications/{self.carol.pk}/").status_code, 404)

    def test_candidates_are_refused(self):
        self.login_as("candidate", "alice@example.com")
        self.assertEqual(self.client.get(f"/api/applications/{self.alice.pk}/").status_code, 403)


class StatusTests(Base):
    def patch(self, pk, payload):
        return self.client.patch(f"/api/applications/{pk}/status/", payload, format="json")

    def test_recruiter_can_shortlist_reject_and_reset(self):
        for value in ("shortlisted", "rejected", "applied"):
            res = self.patch(self.alice.pk, {"status": value})
            self.assertEqual(res.status_code, 200, value)
            self.assertEqual(res.data["status"], value)
            self.alice.refresh_from_db()
            self.assertEqual(self.alice.status, value)

    def test_interview_scheduled_cannot_be_set_here(self):
        res = self.patch(self.alice.pk, {"status": "interview_scheduled"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("status", res.data["errors"])

    def test_invalid_and_extra_fields_are_rejected(self):
        self.assertEqual(self.patch(self.alice.pk, {"status": "hired"}).status_code, 400)
        self.assertEqual(self.patch(self.alice.pk, {}).status_code, 400)
        self.assertEqual(self.patch(self.alice.pk, {"status": "rejected", "job": 1}).status_code, 400)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.status, "applied")

    def test_another_recruiters_application_is_404_and_unchanged(self):
        self.assertEqual(self.patch(self.carol.pk, {"status": "rejected"}).status_code, 404)
        self.carol.refresh_from_db()
        self.assertEqual(self.carol.status, "applied")

    def test_candidates_cannot_change_status(self):
        self.login_as("candidate", "alice@example.com")
        self.assertEqual(self.patch(self.alice.pk, {"status": "shortlisted"}).status_code, 403)

    def test_candidate_sees_the_new_status(self):
        self.patch(self.alice.pk, {"status": "shortlisted"})
        self.login_as("candidate", "alice@example.com")
        res = self.client.get("/api/applications/me/")
        self.assertEqual(res.data["results"][0]["status"], "shortlisted")


class ResumeFileTests(Base):
    def setUp(self):
        super().setUp()
        folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(folder.cleanup)
        override = override_settings(MEDIA_ROOT=folder.name)
        override.enable()
        self.addCleanup(override.disable)

    def test_owner_can_read_the_resume_file(self):
        resume = self.alice.resume
        resume.file.save("cv.pdf", ContentFile(b"%PDF-1.4 test"), save=True)
        res = self.client.get(f"/api/applications/{self.alice.pk}/resume-file/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertIn("inline", res["Content-Disposition"])
        self.assertEqual(b"".join(res.streaming_content), b"%PDF-1.4 test")
        res.close()

    def test_missing_file_gives_404(self):
        res = self.client.get(f"/api/applications/{self.alice.pk}/resume-file/")
        self.assertEqual(res.status_code, 404)

    def test_another_recruiters_file_is_404(self):
        self.carol.resume.file.save("cv.pdf", ContentFile(b"%PDF-1.4 x"), save=True)
        res = self.client.get(f"/api/applications/{self.carol.pk}/resume-file/")
        self.assertEqual(res.status_code, 404)

    def test_candidates_are_refused(self):
        self.login_as("candidate", "alice@example.com")
        self.assertEqual(self.client.get(f"/api/applications/{self.alice.pk}/resume-file/").status_code, 403)