from collections import namedtuple

from django.db.models import F
from pgvector.django import CosineDistance

from applications.models import Application

from ..exceptions import EmbeddingError
from . import search
from .similarity import similarity_to_score

# rank is None for applicants that could not be scored (no resume left, or resume not embedded yet)
RankedApplicant = namedtuple(
    "RankedApplicant",
    ["rank", "application", "similarity", "score", "matching_skills", "missing_skills"],
)

MAX_APPLICANTS = 200


def skill_overlap(resume_skills, job_skills):
    """Compares skill NAMES literally (ignoring upper/lower case). Nothing is guessed.

    Returns (matching, missing): the job's required skills that the resume does / does not list.
    """
    have = {name.lower() for name in resume_skills}
    matching = sorted((name for name in job_skills if name.lower() in have), key=str.lower)
    missing = sorted((name for name in job_skills if name.lower() not in have), key=str.lower)
    return matching, missing


def _check_limit(limit):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_APPLICANTS:
        raise ValueError(f"limit must be a whole number from 1 to {MAX_APPLICANTS}.")


def rank_applicants(job, limit=50):
    """The applicants of ONE job, best semantic match first (decision support for the recruiter).

    The score compares the resume each candidate APPLIED WITH to the job, using the vectors in
    PostgreSQL. Applicants that cannot be scored are not hidden: they are listed after the ranked
    ones (rank None), oldest application first.

    Returns (rows, total_applicants, scored_applicants).
    """
    _check_limit(limit)
    if job.embedding is None:
        raise EmbeddingError("This job has not been embedded yet.")

    applications = Application.objects.filter(job=job)
    total = applications.count()
    scored = applications.filter(resume__embedding__isnull=False).count()

    queryset = (
        applications.select_related("candidate__user", "resume")
        .prefetch_related("resume__skills")
        .annotate(distance=CosineDistance("resume__embedding", job.embedding))
        .order_by(F("distance").asc(nulls_last=True), "applied_at", "pk")[:limit]
    )
    job_skills = [skill.name for skill in job.required_skills.all()]

    rows, position = [], 0
    for application in queryset:
        resume_skills = [skill.name for skill in application.resume.skills.all()] if application.resume else []
        matching, missing = skill_overlap(resume_skills, job_skills)
        if application.distance is None:
            rows.append(RankedApplicant(None, application, None, None, matching, missing))
        else:
            position += 1
            similarity = max(-1.0, min(1.0, 1.0 - float(application.distance)))
            rows.append(
                RankedApplicant(position, application, similarity, similarity_to_score(similarity), matching, missing)
            )
    return rows, total, scored


Recommendation = namedtuple(
    "Recommendation", ["job", "similarity", "score", "matching_skills", "missing_skills", "already_applied"]
)


def recommend_jobs(resume, candidate, queryset, limit=10, include_applied=False, min_percent=0.0):
    """Active jobs most similar to the candidate's resume, best first.

    `queryset` is the (already filtered) set of jobs to choose from. Jobs the candidate has
    already applied to are left out unless include_applied is True.
    """
    applied_ids = set(Application.objects.filter(candidate=candidate).values_list("job_id", flat=True))
    if not include_applied:
        queryset = queryset.exclude(pk__in=applied_ids)

    resume_skills = [skill.name for skill in resume.skills.all()]
    results = []
    for hit in search.search_jobs_for_resume(resume, queryset=queryset, limit=limit):
        if hit.score < min_percent:
            break  # results are sorted, so everything after this one is lower still
        job_skills = [skill.name for skill in hit.item.required_skills.all()]
        matching, missing = skill_overlap(resume_skills, job_skills)
        results.append(
            Recommendation(hit.item, hit.similarity, hit.score, matching, missing, hit.item.pk in applied_ids)
        )
    return results