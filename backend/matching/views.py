from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCandidate, IsRecruiter
from candidates.models import Candidate
from jobs.filters import apply_job_filters
from jobs.models import Job
from jobs.serializers import JobSerializer
from resumes.models import Resume

from .exceptions import EmbeddingError
from .services import embeddings, ranking, search, storage

MIN_QUERY_CHARS, MAX_QUERY_CHARS = 3, 500
DEFAULT_LIMIT, MAX_LIMIT = 10, 50
DEFAULT_APPLICANT_LIMIT = 50


class SemanticSearchUnavailable(APIException):
    status_code = 503
    default_detail = "Semantic search is temporarily unavailable. Please try again later."
    default_code = "search_unavailable"


class RankingUnavailable(APIException):
    status_code = 503
    default_detail = "Ranking is temporarily unavailable because this job has not been processed yet. Please try again later."
    default_code = "ranking_unavailable"


class RecommendationsUnavailable(APIException):
    status_code = 503
    default_detail = "Recommendations are temporarily unavailable because your resume has not been processed yet. Please try again later."
    default_code = "recommendations_unavailable"


def whole_number_param(params, name, default, maximum):
    raw = params.get(name, str(default)).strip()
    if not raw.isdigit() or not 1 <= int(raw) <= maximum:
        raise ValidationError({name: [f"Use a whole number from 1 to {maximum}."]})
    return int(raw)


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

        limit = whole_number_param(params, "limit", DEFAULT_LIMIT, MAX_LIMIT)

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


def applicant_payload(row):
    application = row.application
    candidate = application.candidate
    user = candidate.user
    resume = application.resume
    return {
        "rank": row.rank,
        "scored": row.rank is not None,
        "application_id": application.id,
        "status": application.status,
        "applied_at": application.applied_at,
        "candidate": {
            "id": candidate.id,
            "name": f"{user.first_name} {user.last_name}".strip(),
            "email": user.email,
            "headline": candidate.headline,
            "university": candidate.university,
            "degree": candidate.degree,
            "graduation_year": candidate.graduation_year,
            "location": candidate.location,
            "linkedin_url": candidate.linkedin_url,
            "github_url": candidate.github_url,
        },
        "resume": None
        if resume is None
        else {
            "id": resume.id,
            "original_filename": resume.original_filename,
            "uploaded_at": resume.uploaded_at,
            "skills": [skill.name for skill in resume.skills.all()],
        },
        "cosine_similarity": None if row.similarity is None else round(row.similarity, 4),
        "match_percent": row.score,
        "matching_skills": row.matching_skills,
        "missing_skills": row.missing_skills,
    }


class JobRankingView(APIView):
    """GET /api/matching/jobs/<job_id>/ranking/   (recruiter, own jobs only)

    The applicants of one job ordered by how semantically close the resume they applied with is to
    the job. This is decision support: the recruiter reviews the candidates and decides.
    """

    permission_classes = [IsAuthenticated, IsRecruiter]

    def get(self, request, job_id):
        jobs = Job.objects.filter(recruiter__user=request.user).prefetch_related("required_skills")
        job = get_object_or_404(jobs, pk=job_id)  # someone else's job gives 404
        limit = whole_number_param(request.query_params, "limit", DEFAULT_APPLICANT_LIMIT, ranking.MAX_APPLICANTS)

        if job.embedding is None:
            storage.embed_job_safely(job)
        try:
            rows, total, scored = ranking.rank_applicants(job, limit=limit)
        except EmbeddingError:
            raise RankingUnavailable()

        return Response(
            {
                "job": {"id": job.id, "job_title": job.job_title, "company_name": job.company_name, "is_active": job.is_active},
                "note": (
                    "AI-assisted ranking to help you prioritise your review. It is not a hiring decision; "
                    "always read the resumes and decide yourself."
                ),
                "applicants_total": total,
                "applicants_scored": scored,
                "results": [applicant_payload(row) for row in rows],
            }
        )


def true_false_param(params, name):
    raw = params.get(name, "false").strip().lower()
    if raw in ("true", "1"):
        return True
    if raw in ("false", "0"):
        return False
    raise ValidationError({name: ["Use true or false."]})


def percent_param(params, name):
    raw = params.get(name, "0").strip()
    try:
        value = float(raw)
    except ValueError:
        value = float("nan")
    if not 0 <= value <= 100:  # also rejects nan
        raise ValidationError({name: ["Use a number from 0 to 100."]})
    return value


class JobRecommendationsView(APIView):
    """GET /api/matching/recommendations/   (candidate)

    Active jobs ranked by how close they are to the candidate's ACTIVE resume. Jobs already applied
    to are left out unless include_applied=true. The normal job filters can be combined with it.
    Extra options: limit (1-50), min_percent (0-100).
    """

    permission_classes = [IsAuthenticated, IsCandidate]

    def get(self, request):
        params = request.query_params
        limit = whole_number_param(params, "limit", DEFAULT_LIMIT, MAX_LIMIT)
        min_percent = percent_param(params, "min_percent")
        include_applied = true_false_param(params, "include_applied")
        if "ordering" in params:
            raise ValidationError({"ordering": ["Results are ordered by similarity; remove this parameter."]})

        candidate, _ = Candidate.objects.get_or_create(user=request.user)
        resume = (
            Resume.objects.filter(candidate=candidate, is_active=True, parsing_status=Resume.ParsingStatus.SUCCESS)
            .prefetch_related("skills")
            .first()
        )
        if resume is None:
            raise ValidationError({"resume": ["Upload a resume to get job recommendations."]})
        if resume.embedding is None:
            storage.embed_resume_safely(resume)
        if resume.embedding is None:
            raise RecommendationsUnavailable()

        jobs = apply_job_filters(Job.objects.filter(is_active=True).prefetch_related("required_skills"), params)
        results = ranking.recommend_jobs(
            resume, candidate, jobs, limit=limit, include_applied=include_applied, min_percent=min_percent
        )
        return Response(
            {
                "resume": {"id": resume.id, "original_filename": resume.original_filename},
                "count": len(results),
                "results": [
                    {
                        "job": JobSerializer(row.job).data,
                        "cosine_similarity": round(row.similarity, 4),
                        "match_percent": row.score,
                        "matching_skills": row.matching_skills,
                        "missing_skills": row.missing_skills,
                        "already_applied": row.already_applied,
                    }
                    for row in results
                ],
            }
        )