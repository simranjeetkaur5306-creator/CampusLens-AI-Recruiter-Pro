from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from accounts.models import User
from candidates.models import Candidate
from jobs.models import Job
from jobs.services import resolve_skills
from recruiters.models import Recruiter
from resumes.models import Resume

from .fakes import FakeModel

PATCH_MODEL = "matching.services.embeddings.get_model"


class MatchCheckCommandTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="c@example.com", email="c@example.com", password="x", role="candidate")
        candidate = Candidate.objects.create(user=user)
        rec_user = User.objects.create_user(username="r@example.com", email="r@example.com", password="x", role="recruiter")
        recruiter = Recruiter.objects.create(user=rec_user, company_name="Acme")
        self.resume = Resume.objects.create(
            candidate=candidate, file="resumes/1/x.pdf", original_filename="x.pdf", file_type="pdf", file_size=1,
            parsing_status="success", extracted_text="Built backend REST APIs with Python and Django for a college portal.",
        )
        self.resume.skills.set(resolve_skills(["Python", "Django", "Docker"]))
        self.job = Job.objects.create(
            recruiter=recruiter, job_title="Backend Developer", company_name="Acme", location="Pune",
            description="Build REST APIs with Python and Django for our hiring platform.",
        )
        self.job.required_skills.set(resolve_skills(["Python", "Django", "SQL"]))

    def run_command(self, **kwargs):
        out = StringIO()
        with mock.patch(PATCH_MODEL, return_value=FakeModel()):
            call_command("match_check", stdout=out, **kwargs)
        return out.getvalue()

    def test_prints_score_and_skill_overlap(self):
        text = self.run_command(resume_id=self.resume.pk, job_id=self.job.pk)
        self.assertIn("Cosine similarity:", text)
        self.assertIn("Matching score:", text)
        self.assertIn("Job skills found in the resume: Django, Python", text)
        self.assertIn("Job skills not found in the resume: SQL", text)

    def test_unknown_ids_are_command_errors(self):
        with self.assertRaises(CommandError):
            self.run_command(resume_id=9999, job_id=self.job.pk)
        with self.assertRaises(CommandError):
            self.run_command(resume_id=self.resume.pk, job_id=9999)

    def test_unparsed_resume_is_a_command_error(self):
        Resume.objects.filter(pk=self.resume.pk).update(parsing_status="failed")
        with self.assertRaises(CommandError) as ctx:
            self.run_command(resume_id=self.resume.pk, job_id=self.job.pk)
        self.assertIn("not parsed successfully", str(ctx.exception))