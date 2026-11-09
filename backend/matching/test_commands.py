from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from jobs.models import Job
from resumes.models import Resume

from .exceptions import EmbeddingError
from .factories import make_candidate, make_job, make_recruiter, make_resume, set_embedding, vector
from .services import search as search_module
from .services import storage


class EmbedAllCommandTests(TestCase):
    def setUp(self):
        self.resume = make_resume(make_candidate("a@example.com"))
        self.failed_resume = make_resume(make_candidate("b@example.com"), status="failed", active=False)
        self.job1 = make_job(make_recruiter(), title="First job")
        self.job2 = make_job(make_recruiter("r2@example.com"), title="Second job", active=False)

    def run_command(self, *args):
        out, err = StringIO(), StringIO()
        call_command("embed_all", *args, stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

    def test_fills_in_missing_embeddings(self):
        out, _err = self.run_command()
        self.assertIn("resumes embedded: 1, failed: 0", out)
        self.assertIn("jobs embedded: 2, failed: 0", out)
        self.assertEqual(Resume.objects.filter(embedding__isnull=False).count(), 1)
        self.assertEqual(Job.objects.filter(embedding__isnull=False).count(), 2)

    def test_resumes_that_failed_parsing_are_skipped(self):
        self.run_command()
        self.failed_resume.refresh_from_db()
        self.assertIsNone(self.failed_resume.embedding)

    def test_existing_embeddings_are_left_alone(self):
        self.run_command()
        with mock.patch("matching.services.storage.embed_resume") as embed_resume, \
                mock.patch("matching.services.storage.embed_job") as embed_job:
            out, _err = self.run_command()
        embed_resume.assert_not_called()
        embed_job.assert_not_called()
        self.assertIn("resumes embedded: 0", out)

    def test_force_rebuilds_everything(self):
        self.run_command()
        with mock.patch("matching.services.storage.embed_resume") as embed_resume, \
                mock.patch("matching.services.storage.embed_job") as embed_job:
            self.run_command("--force")
        self.assertEqual(embed_resume.call_count, 1)
        self.assertEqual(embed_job.call_count, 2)

    def test_only_option(self):
        self.run_command("--only", "jobs")
        self.assertEqual(Job.objects.filter(embedding__isnull=False).count(), 2)
        self.assertEqual(Resume.objects.filter(embedding__isnull=False).count(), 0)
        self.run_command("--only", "resumes")
        self.assertEqual(Resume.objects.filter(embedding__isnull=False).count(), 1)

    def test_one_failure_does_not_stop_the_others_but_is_reported(self):
        real = storage.embed_job

        def flaky(job):
            if job.pk == self.job1.pk:
                raise EmbeddingError("boom")
            return real(job)

        with mock.patch("matching.services.storage.embed_job", side_effect=flaky):
            out, err = StringIO(), StringIO()
            with self.assertRaises(CommandError) as ctx:
                call_command("embed_all", stdout=out, stderr=err)
        self.assertIn("could not be embedded", str(ctx.exception))
        self.assertIn(f"Could not embed job {self.job1.pk}", err.getvalue())
        self.assertIsNotNone(Job.objects.get(pk=self.job2.pk).embedding)
        self.assertIsNone(Job.objects.get(pk=self.job1.pk).embedding)

    def test_unavailable_model_gives_one_clear_error(self):
        with mock.patch("matching.services.embeddings.get_model", side_effect=EmbeddingError("model missing")):
            with self.assertRaises(CommandError) as ctx:
                self.run_command()
        self.assertIn("model missing", str(ctx.exception))


class SemanticSearchCommandTests(TestCase):
    def setUp(self):
        recruiter = make_recruiter()
        self.best = make_job(recruiter, title="Best match")
        self.other = make_job(recruiter, title="Other match")
        set_embedding(self.best, vector(1, 0.05))
        set_embedding(self.other, vector(0.2, 1))
        self.resume = make_resume(make_candidate())
        set_embedding(self.resume, vector(1, 0))

    def run_command(self, **kwargs):
        out = StringIO()
        call_command("semantic_search", stdout=out, **kwargs)
        return out.getvalue()

    def test_search_by_resume(self):
        text = self.run_command(resume_id=self.resume.pk)
        self.assertIn("1. [%d] Best match" % self.best.pk, text)
        self.assertIn("2. [%d] Other match" % self.other.pk, text)
        self.assertIn("cosine", text)

    def test_search_by_text_and_limit(self):
        text = self.run_command(query="backend developer python django", limit=1)
        self.assertIn("Query: backend developer python django", text)
        self.assertEqual(text.count("cosine"), 1)

    def test_verify_confirms_pgvector_matches_python(self):
        text = self.run_command(resume_id=self.resume.pk, verify=True)
        self.assertIn("VERIFY OK", text)

    def test_verify_fails_when_the_ranking_is_wrong(self):
        real = search_module.search_jobs

        def reversed_results(*args, **kwargs):
            return list(reversed(real(*args, **kwargs)))

        with mock.patch("matching.management.commands.semantic_search.search.search_jobs", side_effect=reversed_results):
            with self.assertRaises(CommandError) as ctx:
                self.run_command(resume_id=self.resume.pk, verify=True)
        self.assertIn("VERIFY FAILED", str(ctx.exception))

    def test_exactly_one_input_is_required(self):
        with self.assertRaises(CommandError):
            self.run_command()
        with self.assertRaises(CommandError):
            self.run_command(resume_id=self.resume.pk, query="python developer")

    def test_unknown_or_unembedded_resume(self):
        with self.assertRaises(CommandError):
            self.run_command(resume_id=99999)
        fresh = make_resume(make_candidate("n@example.com"))
        with self.assertRaises(CommandError) as ctx:
            self.run_command(resume_id=fresh.pk)
        self.assertIn("embed_all", str(ctx.exception))

    def test_invalid_limit_and_text(self):
        with self.assertRaises(CommandError):
            self.run_command(resume_id=self.resume.pk, limit=0)
        with self.assertRaises(CommandError):
            self.run_command(query="   ")

    def test_message_when_no_jobs_have_embeddings(self):
        Job.objects.update(embedding=None)
        self.assertIn("No active jobs", self.run_command(resume_id=self.resume.pk))