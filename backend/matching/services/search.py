from collections import namedtuple

from pgvector.django import CosineDistance

from jobs.models import Job
from resumes.models import Resume

from ..exceptions import EmbeddingError
from . import embeddings
from .similarity import similarity_to_score

MAX_LIMIT = 100

# item = the Job or Resume, similarity = cosine similarity (-1..1), score = percent for display
SearchResult = namedtuple("SearchResult", ["item", "similarity", "score"])


def _check_limit(limit):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be a whole number from 1 to {MAX_LIMIT}.")


def _nearest(queryset, vector, limit):
    """The core pgvector query: order rows by cosine distance to `vector` (smaller = more similar).

    pgvector's <=> operator returns the cosine DISTANCE, which is 1 - cosine similarity.
    """
    _check_limit(limit)
    queryset = (
        queryset.filter(embedding__isnull=False)
        .annotate(distance=CosineDistance("embedding", vector))
        .order_by("distance", "pk")[:limit]
    )
    results = []
    for item in queryset:
        similarity = max(-1.0, min(1.0, 1.0 - float(item.distance)))
        results.append(SearchResult(item, similarity, similarity_to_score(similarity)))
    return results


def search_jobs(vector, queryset=None, limit=10):
    """Active jobs nearest to a vector. Pass `queryset` to restrict or pre-filter the jobs."""
    base = Job.objects.filter(is_active=True) if queryset is None else queryset
    return _nearest(base, vector, limit)


def search_jobs_for_text(text, queryset=None, limit=10):
    """Semantic search with free text, e.g. "building machine learning models"."""
    return search_jobs(embeddings.embed_text(text), queryset=queryset, limit=limit)


def search_jobs_for_resume(resume, queryset=None, limit=10):
    """Jobs most similar to a stored resume (uses the vector saved in the database)."""
    if resume.embedding is None:
        raise EmbeddingError("This resume has not been embedded yet.")
    return search_jobs(resume.embedding, queryset=queryset, limit=limit)


def search_resumes_for_job(job, queryset=None, limit=10):
    """Resumes most similar to a stored job.

    By default this looks at every candidate's ACTIVE, successfully parsed resume. Callers that
    must only see certain candidates (for example the applicants of one job) pass `queryset`.
    """
    if job.embedding is None:
        raise EmbeddingError("This job has not been embedded yet.")
    base = (
        Resume.objects.filter(parsing_status=Resume.ParsingStatus.SUCCESS, is_active=True)
        if queryset is None
        else queryset
    )
    return _nearest(base, job.embedding, limit)