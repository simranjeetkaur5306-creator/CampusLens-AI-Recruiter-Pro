"""Recruitment analytics for ONE recruiter.

Every number here is calculated from the database when the request arrives (nothing is
stored or hard-coded). Counting uses database aggregation (Count / Avg / TruncDate); only the
skill-gap list is assembled in Python, because it compares two sets of skill names per applicant.
"""
from collections import Counter
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from pgvector.django import CosineDistance

from applications.models import Application
from jobs.models import Job
from matching.services.ranking import skill_overlap
from matching.services.similarity import similarity_to_score
from resumes.models import Skill

DEFAULT_DAYS = 30
MIN_DAYS = 7
MAX_DAYS = 90
TOP_N = 10
MAX_GAP_APPLICATIONS = 2000  # newest applications considered for the skill-gap list

Status = Application.Status


def _count(status):
    return Count("id", filter=Q(status=status))


def _status_counts():
    return {
        "total": Count("id"),
        "applied": _count(Status.APPLIED),
        "shortlisted": _count(Status.SHORTLISTED),
        "rejected": _count(Status.REJECTED),
        "interviews": _count(Status.INTERVIEW_SCHEDULED),
    }


def _applications_per_day(applications, days):
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    rows = (
        applications.filter(applied_at__date__gte=start)
        .order_by()
        .annotate(day=TruncDate("applied_at"))
        .values("day")
        .annotate(count=Count("id"))
    )
    per_day = {row["day"]: row["count"] for row in rows}
    series = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        series.append({"date": day.isoformat(), "count": per_day.get(day, 0)})
    return series


def _top_candidate_skills(recruiter):
    """Skills most often listed on the resumes that applied to this recruiter's jobs."""
    skills = (
        Skill.objects.filter(resumes__applications__job__recruiter=recruiter)
        .annotate(count=Count("resumes__applications", distinct=True))
        .order_by("-count", "name")[:TOP_N]
    )
    return [{"skill": skill.name, "count": skill.count} for skill in skills]


def _common_skill_gaps(applications, job_skills):
    """Required skills that applicants most often do NOT list (same exact-name rule as the ranking page)."""
    counter, display, analysed = Counter(), {}, 0
    queryset = (
        applications.filter(resume__isnull=False)
        .select_related("resume")
        .prefetch_related("resume__skills")
        .order_by("-applied_at")[:MAX_GAP_APPLICATIONS]
    )
    for application in queryset:
        analysed += 1
        have = [skill.name for skill in application.resume.skills.all()]
        _, missing = skill_overlap(have, job_skills.get(application.job_id, []))
        for name in missing:
            key = name.lower()
            counter[key] += 1
            display.setdefault(key, name)
    rows = sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:TOP_N]
    gaps = [
        {"skill": display[key], "count": count, "share_percent": round(100.0 * count / analysed, 1)}
        for key, count in rows
    ]
    return gaps, analysed


def _match_scores(jobs, applications):
    """Average cosine similarity (as a percent) per job and overall, computed inside PostgreSQL.

    Only applications whose resume has a vector are counted, and jobs without a vector are skipped.
    Returns (overall_percent_or_None, scored_count, {job_id: percent}).
    """
    weighted_sum, scored, per_job = 0.0, 0, {}
    for job in jobs:
        if job.embedding is None:
            continue
        aggregate = (
            applications.filter(job=job, resume__embedding__isnull=False)
            .annotate(distance=CosineDistance("resume__embedding", job.embedding))
            .aggregate(avg=Avg("distance"), n=Count("id"))
        )
        if not aggregate["n"] or aggregate["avg"] is None:
            continue
        similarity = max(-1.0, min(1.0, 1.0 - float(aggregate["avg"])))
        per_job[job.pk] = similarity_to_score(similarity)
        weighted_sum += similarity * aggregate["n"]
        scored += aggregate["n"]
    overall = similarity_to_score(weighted_sum / scored) if scored else None
    return overall, scored, per_job


def recruiter_overview(recruiter, days=DEFAULT_DAYS):
    jobs = list(Job.objects.filter(recruiter=recruiter).prefetch_related("required_skills"))
    applications = Application.objects.filter(job__recruiter=recruiter)

    totals = applications.aggregate(**_status_counts())
    per_job = {
        row["job_id"]: row
        for row in applications.order_by().values("job_id").annotate(**_status_counts())
    }
    job_skills = {job.pk: [skill.name for skill in job.required_skills.all()] for job in jobs}

    gaps, gaps_analysed = _common_skill_gaps(applications, job_skills)
    overall_score, scored, job_scores = _match_scores(jobs, applications)

    by_status = {
        Status.APPLIED: totals["applied"],
        Status.SHORTLISTED: totals["shortlisted"],
        Status.REJECTED: totals["rejected"],
        Status.INTERVIEW_SCHEDULED: totals["interviews"],
    }

    return {
        "totals": {
            "jobs_posted": len(jobs),
            "jobs_published": sum(1 for job in jobs if job.is_active),
            "applications": totals["total"],
            "awaiting_review": totals["applied"],
            "shortlisted": totals["shortlisted"],
            "rejected": totals["rejected"],
            "interviews_scheduled": totals["interviews"],
        },
        "status_distribution": [
            {"status": value, "label": label, "count": by_status[value]} for value, label in Status.choices
        ],
        "applications_over_time": {"days": days, "points": _applications_per_day(applications, days)},
        "matching": {
            "average_score": overall_score,
            "scored_applications": scored,
            "total_applications": totals["total"],
        },
        "top_candidate_skills": _top_candidate_skills(recruiter),
        "common_skill_gaps": {"analysed_applications": gaps_analysed, "items": gaps},
        "jobs": [
            {
                "id": job.pk,
                "job_title": job.job_title,
                "is_active": job.is_active,
                "applications": per_job.get(job.pk, {}).get("total", 0),
                "awaiting_review": per_job.get(job.pk, {}).get("applied", 0),
                "shortlisted": per_job.get(job.pk, {}).get("shortlisted", 0),
                "rejected": per_job.get(job.pk, {}).get("rejected", 0),
                "interviews_scheduled": per_job.get(job.pk, {}).get("interviews", 0),
                "average_score": job_scores.get(job.pk),
            }
            for job in jobs
        ],
        "generated_at": timezone.now(),
        "notes": [
            "Match scores are raw embedding similarity between each resume and its job. They are not a "
            "prediction of hiring success, and applications without a resume vector are not counted.",
            "Skill gaps compare skill names exactly (ignoring upper/lower case), the same rule as the "
            "candidate ranking page.",
        ],
    }