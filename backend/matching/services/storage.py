import logging

from django.conf import settings
from django.utils import timezone

from jobs.models import Job
from resumes.models import Resume

from . import embeddings

logger = logging.getLogger(__name__)


def embed_resume(resume):
    """Creates the resume's vector and saves it in PostgreSQL (pgvector). Raises on failure."""
    vector = embeddings.embed_text(embeddings.resume_document(resume))
    now = timezone.now()
    # .update() writes only these columns (no full save, no signals)
    Resume.objects.filter(pk=resume.pk).update(
        embedding=vector, embedding_model=settings.EMBEDDING_MODEL_NAME, embedded_at=now
    )
    resume.embedding, resume.embedding_model, resume.embedded_at = vector, settings.EMBEDDING_MODEL_NAME, now
    return vector


def embed_job(job):
    """Creates the job's vector and saves it in PostgreSQL (pgvector). Raises on failure."""
    vector = embeddings.embed_text(embeddings.job_document(job))
    now = timezone.now()
    Job.objects.filter(pk=job.pk).update(
        embedding=vector, embedding_model=settings.EMBEDDING_MODEL_NAME, embedded_at=now
    )  # .update() also leaves updated_at untouched
    job.embedding, job.embedding_model, job.embedded_at = vector, settings.EMBEDDING_MODEL_NAME, now
    return vector


def clear_job_embedding(job):
    Job.objects.filter(pk=job.pk).update(embedding=None, embedding_model="", embedded_at=None)
    job.embedding, job.embedding_model, job.embedded_at = None, "", None


def embed_resume_safely(resume):
    """Like embed_resume, but never raises: a model problem must not break a resume upload.

    The resume then simply has no vector yet; `manage.py embed_all` creates it later.
    """
    try:
        embed_resume(resume)
        return True
    except Exception:
        logger.exception("Could not embed resume %s", resume.pk)
        return False


def embed_job_safely(job):
    """Like embed_job, but never raises. On failure the old vector is removed: a job whose text
    has changed must not stay searchable under its outdated meaning."""
    try:
        embed_job(job)
        return True
    except Exception:
        logger.exception("Could not embed job %s", job.pk)
        try:
            clear_job_embedding(job)
        except Exception:
            logger.exception("Could not clear the outdated embedding of job %s", job.pk)
        return False