import os
import sys
from io import StringIO
from unittest import mock, skipUnless

import numpy as np
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings

from accounts.models import User
from candidates.models import Candidate
from jobs.models import Job
from jobs.services import resolve_skills
from recruiters.models import Recruiter
from resumes.models import Resume

from .exceptions import EmbeddingError
from .fakes import DIMENSIONS, FakeModel
from .services import embeddings
from .services.embeddings import (
    chunk_text,
    embed_text,
    embed_texts,
    job_document,
    prepare_text,
    resume_document,
)
from .services.similarity import cosine_similarity

PATCH_MODEL = "matching.services.embeddings.get_model"


def with_fake_model():
    fake = FakeModel()
    return fake, mock.patch(PATCH_MODEL, return_value=fake)


class PrepareTextTests(SimpleTestCase):
    def test_removes_contact_details_but_keeps_content(self):
        raw = (
            "Simran Kaur  simran@example.com  +91 98765 43210\n"
            "linkedin.com/in/simran-kaur  https://github.com/simran-dev\n"
            "B.Tech 2023 - 2027, Python and SQL"
        )
        cleaned = prepare_text(raw)
        self.assertNotIn("@", cleaned)
        self.assertNotIn("98765", cleaned)
        self.assertNotIn("linkedin", cleaned)
        self.assertNotIn("github", cleaned)
        self.assertIn("2023 - 2027", cleaned)  # a year range is not a phone number
        self.assertIn("Python and SQL", cleaned)

    def test_whitespace_is_collapsed(self):
        self.assertEqual(prepare_text("Python\n\n  and \t SQL   skills"), "Python and SQL skills")

    def test_invalid_text_raises_embedding_error(self):
        for bad in (None, 123, ["text"], b"bytes", "", "   ", "!!! ???", "short"):
            with self.assertRaises(EmbeddingError, msg=repr(bad)):
                prepare_text(bad)


class ChunkTextTests(SimpleTestCase):
    def words(self, n):
        return " ".join(f"w{i}" for i in range(n))

    def test_short_text_is_one_chunk(self):
        self.assertEqual(chunk_text(self.words(50), words=128, overlap=20), [self.words(50)])

    def test_long_text_gives_overlapping_chunks_that_cover_everything(self):
        chunks = chunk_text(self.words(300), words=128, overlap=20, max_chunks=16)
        self.assertEqual(len(chunks), 3)
        self.assertTrue(all(len(c.split()) <= 128 for c in chunks))
        self.assertEqual(chunks[0].split()[-20:], chunks[1].split()[:20])  # overlap
        self.assertEqual(chunks[-1].split()[-1], "w299")  # reaches the end

    def test_exact_size_text_is_not_split(self):
        self.assertEqual(len(chunk_text(self.words(128), words=128, overlap=20)), 1)

    def test_max_chunks_is_respected(self):
        self.assertEqual(len(chunk_text(self.words(5000), words=128, overlap=20, max_chunks=4)), 4)

    def test_no_empty_chunks(self):
        for n in (1, 127, 128, 129, 148, 149, 150, 400):
            chunks = chunk_text(self.words(n), words=128, overlap=20)
            self.assertTrue(all(c.strip() for c in chunks), n)


class EmbedTextTests(SimpleTestCase):
    def test_returns_unit_vector_with_configured_dimensions(self):
        _fake, patch = with_fake_model()
        with patch:
            vector = embed_text("Python developer with Django and SQL experience")
        self.assertEqual(len(vector), DIMENSIONS)
        self.assertTrue(all(isinstance(x, float) for x in vector))
        self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0, places=5)

    def test_same_text_gives_same_vector(self):
        _fake, patch = with_fake_model()
        with patch:
            a = embed_text("Python developer with Django and SQL experience")
            b = embed_text("Python developer with Django and SQL experience")
        self.assertEqual(a, b)

    def test_contact_details_do_not_change_the_vector(self):
        _fake, patch = with_fake_model()
        with patch:
            plain = embed_text("Python developer with Django and SQL experience")
            noisy = embed_text("Python developer with Django and SQL experience simran@example.com +91 98765 43210")
        self.assertAlmostEqual(cosine_similarity(plain, noisy), 1.0, places=5)

    def test_long_text_is_embedded_in_several_chunks_and_averaged(self):
        fake, patch = with_fake_model()
        text = " ".join(f"skill{i}" for i in range(400))
        with patch:
            vector = embed_text(text)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(len(fake.calls[0]), 4)  # 400 words -> 4 chunks of up to 128 words
        self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0, places=5)

    def test_invalid_text_never_reaches_the_model(self):
        with mock.patch(PATCH_MODEL) as get_model:
            for bad in (None, "", "   ", 42):
                with self.assertRaises(EmbeddingError):
                    embed_text(bad)
            get_model.assert_not_called()

    def test_embed_texts_returns_one_vector_per_text(self):
        _fake, patch = with_fake_model()
        with patch:
            vectors = embed_texts(["Python and Django backend", "React and CSS frontend"])
        self.assertEqual(len(vectors), 2)
        self.assertEqual(len(vectors[0]), DIMENSIONS)

    def test_related_texts_score_higher_than_unrelated_texts(self):
        _fake, patch = with_fake_model()
        with patch:
            resume = embed_text("Backend developer experienced in Python, Django, SQL and REST API design")
            job = embed_text("We need a backend developer with Python, Django and SQL skills to build REST API services")
            unrelated = embed_text("Restaurant chef who prepares pasta, manages the kitchen and plans menus")
        self.assertGreater(cosine_similarity(resume, job), cosine_similarity(resume, unrelated))

    def test_model_returning_wrong_dimensions_is_rejected(self):
        bad_model = mock.Mock()
        bad_model.encode.return_value = np.ones((1, 10), dtype=np.float32)
        with mock.patch(PATCH_MODEL, return_value=bad_model):
            with self.assertRaises(EmbeddingError):
                embed_text("Python developer with Django and SQL experience")

    def test_model_returning_nan_is_rejected(self):
        bad_model = mock.Mock()
        bad_model.encode.return_value = np.full((1, DIMENSIONS), np.nan, dtype=np.float32)
        with mock.patch(PATCH_MODEL, return_value=bad_model):
            with self.assertRaises(EmbeddingError):
                embed_text("Python developer with Django and SQL experience")

    def test_model_returning_all_zeros_is_rejected(self):
        bad_model = mock.Mock()
        bad_model.encode.return_value = np.zeros((1, DIMENSIONS), dtype=np.float32)
        with mock.patch(PATCH_MODEL, return_value=bad_model):
            with self.assertRaises(EmbeddingError):
                embed_text("Python developer with Django and SQL experience")

    def test_model_exception_becomes_embedding_error(self):
        broken = mock.Mock()
        broken.encode.side_effect = RuntimeError("boom")
        with mock.patch(PATCH_MODEL, return_value=broken):
            with self.assertLogs("matching.services.embeddings", level="ERROR"):
                with self.assertRaises(EmbeddingError):
                    embed_text("Python developer with Django and SQL experience")

    @override_settings(EMBEDDING_FAKE=False)
    def test_missing_library_gives_a_clear_error(self):
        with mock.patch.object(embeddings, "_model", None):
            with mock.patch.dict(sys.modules, {"sentence_transformers": None}):
                with self.assertLogs("matching.services.embeddings", level="ERROR"):
                    with self.assertRaises(EmbeddingError) as ctx:
                        embeddings.get_model()
        self.assertIn("could not be loaded", str(ctx.exception))

    @override_settings(EMBEDDING_DIMENSIONS=999, EMBEDDING_FAKE=False)
    def test_dimension_mismatch_between_model_and_setting_is_reported(self):
        fake_module = mock.Mock()
        fake_module.SentenceTransformer.return_value.get_sentence_embedding_dimension.return_value = 384
        with mock.patch.object(embeddings, "_model", None):
            with mock.patch.dict(sys.modules, {"sentence_transformers": fake_module}):
                with self.assertRaises(EmbeddingError) as ctx:
                    embeddings.get_model()
        self.assertIn("384", str(ctx.exception))


class DocumentTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="c@example.com", email="c@example.com", password="x", role="candidate")
        self.candidate = Candidate.objects.create(user=user)
        rec_user = User.objects.create_user(username="r@example.com", email="r@example.com", password="x", role="recruiter")
        self.recruiter = Recruiter.objects.create(user=rec_user, company_name="Acme")

    def test_resume_document_has_skills_then_text(self):
        resume = Resume.objects.create(
            candidate=self.candidate, file="resumes/1/x.pdf", original_filename="x.pdf",
            file_type="pdf", file_size=1, extracted_text="Built an NLP pipeline for text classification.",
        )
        resume.skills.set(resolve_skills(["Python", "ml"]))
        document = resume_document(resume)
        self.assertTrue(document.startswith("Skills: "))
        self.assertIn("Python", document)
        self.assertIn("Machine Learning", document)
        self.assertTrue(document.endswith("Built an NLP pipeline for text classification."))

    def test_resume_document_without_skills(self):
        resume = Resume.objects.create(
            candidate=self.candidate, file="resumes/1/y.pdf", original_filename="y.pdf",
            file_type="pdf", file_size=1, extracted_text="Some text",
        )
        self.assertEqual(resume_document(resume), "Some text")

    def test_job_document_contains_all_matching_relevant_fields(self):
        job = Job.objects.create(
            recruiter=self.recruiter, job_title="Backend Developer", company_name="Acme", location="Pune",
            description="Build REST APIs for our hiring platform.", required_experience=2,
            required_education="B.Tech in CS",
        )
        job.required_skills.set(resolve_skills(["Python", "Django"]))
        document = job_document(job)
        for part in ("Job title: Backend Developer.", "Required skills: Django, Python.", "Experience required: 2 years.",
                     "Education: B.Tech in CS.", "Build REST APIs for our hiring platform."):
            self.assertIn(part, document)
        self.assertNotIn("Pune", document)   # location is not part of the semantic match
        self.assertNotIn("Acme", document)

    def test_documents_can_be_embedded(self):
        job = Job.objects.create(
            recruiter=self.recruiter, job_title="Backend Developer", company_name="Acme", location="Pune",
            description="Build REST APIs for our hiring platform using Python and Django.",
        )
        _fake, patch = with_fake_model()
        with patch:
            self.assertEqual(len(embed_text(job_document(job))), DIMENSIONS)


class EmbeddingDemoCommandTests(SimpleTestCase):
    """Checks the demo command's own logic with the fake model (the real model is run by the user)."""

    def run_command(self, *args):
        out = StringIO()
        _fake, patch = with_fake_model()
        with patch, mock.patch.object(embeddings, "_model", None):
            call_command("embedding_demo", *args, stdout=out)
        return out.getvalue()

    def test_compare_two_texts(self):
        text = self.run_command("--text-a", "Python backend developer with Django", "--text-b", "Backend developer using Python and Django")
        self.assertIn("Cosine similarity:", text)
        self.assertIn("Matching score:", text)

    def test_only_one_text_is_an_error(self):
        with self.assertRaises(CommandError):
            self.run_command("--text-a", "Only one text given here")

    def test_invalid_text_is_reported_as_command_error(self):
        with self.assertRaises(CommandError):
            self.run_command("--text-a", "", "--text-b", "")

    # The fake model only compares shared words, so it cannot judge meaning. These two tests therefore
    # check the command's PASS/FAIL logic by changing what the command EXPECTS, not the model.
    def test_sample_run_reports_pass_when_expectations_are_met(self):
        what_the_fake_picks = {"ML student": "Frontend Developer", "Web developer": "Frontend Developer",
                               "Restaurant cook": "Restaurant Chef"}
        with mock.patch("matching.management.commands.embedding_demo.EXPECTED_BEST_JOB", what_the_fake_picks):
            text = self.run_command()
        self.assertIn("All sanity checks passed.", text)
        self.assertNotIn("FAIL", text)

    def test_sample_run_fails_loudly_when_expectations_are_not_met(self):
        impossible = {name: "Restaurant Chef" for name in ("ML student", "Web developer", "Restaurant cook")}
        with mock.patch("matching.management.commands.embedding_demo.EXPECTED_BEST_JOB", impossible):
            with self.assertRaises(CommandError) as ctx:
                self.run_command()
        self.assertIn("checks failed", str(ctx.exception))


@skipUnless(os.environ.get("RUN_REAL_EMBEDDING_TESTS") == "1", "set RUN_REAL_EMBEDDING_TESTS=1 to test the real model")
@override_settings(EMBEDDING_FAKE=False)
class RealModelTests(SimpleTestCase):
    """Uses the REAL model (downloads it on first use). Optional: run on your own computer."""

    def test_real_model_dimensions_and_unit_length(self):
        vector = embed_text("Python developer with Django and SQL experience")
        self.assertEqual(len(vector), 384)
        self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0, places=4)

    def test_real_model_understands_meaning_not_just_words(self):
        resume = embed_text("Built predictive models with scikit-learn and pandas and evaluated them with cross-validation")
        related_job = embed_text("Machine learning engineer who develops and deploys ML models")  # different words
        unrelated_job = embed_text("Restaurant chef who plans menus and manages the kitchen team")
        self.assertGreater(cosine_similarity(resume, related_job), cosine_similarity(resume, unrelated_job))

    def test_real_model_sample_demo_passes(self):
        out = StringIO()
        call_command("embedding_demo", stdout=out)
        self.assertIn("All sanity checks passed.", out.getvalue())