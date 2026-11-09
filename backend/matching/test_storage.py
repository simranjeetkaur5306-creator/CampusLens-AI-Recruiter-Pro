from unittest import mock

import numpy as np
from django.conf import settings
from django.db import DataError, connection, transaction
from django.test import TestCase
from pgvector.django import CosineDistance

from jobs.models import Job
from resumes.models import Resume

from .exceptions import EmbeddingError
from .factories import DIMENSIONS, make_candidate, make_job, make_recruiter, make_resume, set_embedding, vector
from .services import embeddings, storage
from .services.similarity import cosine_similarity


class VectorColumnTests(TestCase):
    def setUp(self):
        self.resume = make_resume(make_candidate())
        self.job = make_job(make_recruiter())

    def test_embedding_is_empty_until_created(self):
        self.assertIsNone(self.resume.embedding)
        self.assertEqual(self.resume.embedding_model, "")
        self.assertIsNone(self.resume.embedded_at)
        self.assertIsNone(self.job.embedding)

    def test_vector_round_trip(self):
        values = vector(1, 2, 3)
        set_embedding(self.resume, values)
        set_embedding(self.job, values)
        for obj in (self.resume, self.job):
            self.assertEqual(len(obj.embedding), DIMENSIONS)
            self.assertTrue(np.allclose(obj.embedding, values, atol=1e-6))

    def test_vector_with_wrong_dimension_is_rejected_by_the_database(self):
        with self.assertRaises(DataError), transaction.atomic():
            Resume.objects.filter(pk=self.resume.pk).update(embedding=[1.0, 2.0, 3.0])
        with self.assertRaises(DataError), transaction.atomic():
            Job.objects.filter(pk=self.job.pk).update(embedding=[1.0, 2.0, 3.0])

    def test_settings_match_the_column_size(self):
        self.assertEqual(Resume._meta.get_field("embedding").dimensions, settings.EMBEDDING_DIMENSIONS)
        self.assertEqual(Job._meta.get_field("embedding").dimensions, settings.EMBEDDING_DIMENSIONS)

    def test_hnsw_cosine_indexes_exist(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT indexname, indexdef FROM pg_indexes WHERE indexname = ANY(%s)",
                [["resume_embedding_hnsw", "job_embedding_hnsw"]],
            )
            rows = dict(cursor.fetchall())
        self.assertEqual(set(rows), {"resume_embedding_hnsw", "job_embedding_hnsw"})
        for definition in rows.values():
            self.assertIn("hnsw", definition)
            self.assertIn("vector_cosine_ops", definition)

    def test_planner_can_use_the_hnsw_indexes(self):
        # With only a few rows PostgreSQL rightly prefers a plain scan, so the scan is switched off
        # here to prove that the index fits the query we run (ORDER BY cosine distance LIMIT n).
        probe = "[" + ",".join(["0.05"] * DIMENSIONS) + "]"
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL enable_seqscan = off")
            for table, index in (("resumes_resume", "resume_embedding_hnsw"), ("jobs_job", "job_embedding_hnsw")):
                cursor.execute(f"EXPLAIN SELECT id FROM {table} ORDER BY embedding <=> %s::vector LIMIT 3", [probe])
                plan = "\n".join(row[0] for row in cursor.fetchall())
                self.assertIn(index, plan, plan)

    def test_database_cosine_matches_the_python_formula(self):
        set_embedding(self.resume, vector(1, 0))
        for other in (vector(1, 1), vector(0, 1), vector(-1, 0.2), vector(3, 1, 4, 1, 5)):
            set_embedding(self.job, other)
            distance = Job.objects.annotate(d=CosineDistance("embedding", self.resume.embedding)).get(pk=self.job.pk).d
            self.assertAlmostEqual(1 - distance, cosine_similarity(self.resume.embedding, other), places=5)


class StoreEmbeddingTests(TestCase):
    def setUp(self):
        self.resume = make_resume(make_candidate())
        self.job = make_job(make_recruiter())

    def test_embed_resume_saves_vector_model_and_time(self):
        vector_ = storage.embed_resume(self.resume)
        stored = Resume.objects.get(pk=self.resume.pk)
        self.assertEqual(len(stored.embedding), DIMENSIONS)
        self.assertTrue(np.allclose(stored.embedding, vector_, atol=1e-6))
        self.assertAlmostEqual(float(np.linalg.norm(stored.embedding)), 1.0, places=4)
        self.assertEqual(stored.embedding_model, settings.EMBEDDING_MODEL_NAME)
        self.assertIsNotNone(stored.embedded_at)
        self.assertIsNotNone(self.resume.embedded_at)  # the passed-in object is updated too

    def test_embedded_document_is_the_resume_document(self):
        storage.embed_resume(self.resume)
        expected = embeddings.embed_text(embeddings.resume_document(self.resume))
        self.assertTrue(np.allclose(Resume.objects.get(pk=self.resume.pk).embedding, expected, atol=1e-6))

    def test_embed_job_saves_vector_and_keeps_updated_at(self):
        before = self.job.updated_at
        storage.embed_job(self.job)
        stored = Job.objects.get(pk=self.job.pk)
        self.assertEqual(len(stored.embedding), DIMENSIONS)
        self.assertEqual(stored.embedding_model, settings.EMBEDDING_MODEL_NAME)
        self.assertEqual(stored.updated_at, before)

    def test_failure_raises_and_keeps_the_old_resume_vector(self):
        set_embedding(self.resume, vector(1, 0))
        with mock.patch("matching.services.embeddings.embed_text", side_effect=EmbeddingError("boom")):
            with self.assertRaises(EmbeddingError):
                storage.embed_resume(self.resume)
        self.assertTrue(np.allclose(Resume.objects.get(pk=self.resume.pk).embedding, vector(1, 0), atol=1e-6))

    def test_safe_versions_never_raise(self):
        with mock.patch("matching.services.embeddings.embed_text", side_effect=EmbeddingError("boom")):
            with self.assertLogs("matching.services.storage", level="ERROR"):
                self.assertFalse(storage.embed_resume_safely(self.resume))
            with self.assertLogs("matching.services.storage", level="ERROR"):
                self.assertFalse(storage.embed_job_safely(self.job))

    def test_safe_versions_return_true_on_success(self):
        self.assertTrue(storage.embed_resume_safely(self.resume))
        self.assertTrue(storage.embed_job_safely(self.job))

    def test_failed_job_embedding_removes_the_outdated_vector(self):
        set_embedding(self.job, vector(1, 0))
        with mock.patch("matching.services.embeddings.embed_text", side_effect=EmbeddingError("boom")):
            with self.assertLogs("matching.services.storage", level="ERROR"):
                storage.embed_job_safely(self.job)
        stored = Job.objects.get(pk=self.job.pk)
        self.assertIsNone(stored.embedding)
        self.assertEqual(stored.embedding_model, "")
        self.assertIsNone(stored.embedded_at)