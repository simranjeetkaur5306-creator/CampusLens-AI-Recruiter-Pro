from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCandidate
from jobs.filters import apply_job_filters
from jobs.models import Job
from jobs.serializers import JobSerializer

from .exceptions import EmbeddingError
from .services import embeddings, search

MIN_QUERY_CHARS, MAX_QUERY_CHARS = 3, 500
DEFAULT_LIMIT, MAX_LIMIT = 10, 50


class SemanticSearchUnavailable(APIException):
    status_code = 503
    default_detail = "Semantic search is temporarily unavailable. Please try again later."
    default_code = "search_unavailable"


class JobSemanticSearchView(APIView):
    """GET /api/matching/jobs/search/?q=machine learning models

    Finds active jobs by MEANING (embedding + pgvector), best match first. The normal job filters
    (title, location, company, skills, job_type, max_experience) can be combined with it.
    """

    permission_classes = [IsAuthenticated, IsCandidate]

    def get(self, request):
        params = request.query_params

        query = params.get("q", "").strip()
        if not MIN_QUERY_CHARS <= len(query) <= MAX_QUERY_CHARS:
            raise ValidationError({"q": [f"Enter between {MIN_QUERY_CHARS} and {MAX_QUERY_CHARS} characters."]})
        try:
            embeddings.prepare_text(query)  # rejects text such as "!!!" before the model is used
        except EmbeddingError:
            raise ValidationError({"q": ["Enter a meaningful search text."]})

        raw_limit = params.get("limit", str(DEFAULT_LIMIT)).strip()
        if not raw_limit.isdigit() or not 1 <= int(raw_limit) <= MAX_LIMIT:
            raise ValidationError({"limit": [f"Use a whole number from 1 to {MAX_LIMIT}."]})
        limit = int(raw_limit)

        if "ordering" in params:
            raise ValidationError({"ordering": ["Results are ordered by similarity; remove this parameter."]})

        jobs = apply_job_filters(Job.objects.filter(is_active=True).prefetch_related("required_skills"), params)
        try:
            results = search.search_jobs_for_text(query, queryset=jobs, limit=limit)
        except EmbeddingError:
            raise SemanticSearchUnavailable()

        return Response(
            {
                "query": query,
                "count": len(results),
                "results": [
                    {
                        "job": JobSerializer(row.item).data,
                        "cosine_similarity": round(row.similarity, 4),
                        "match_percent": row.score,
                    }
                    for row in results
                ],
            }
        )