from django.db.models import Q
from rest_framework.exceptions import ValidationError

from .models import Job
from .services import canonical_skill

ALLOWED_ORDERING = {
    "created_at", "-created_at", "job_title", "-job_title",
    "required_experience", "-required_experience",
}
MAX_SKILL_FILTERS = 10


def _bool_param(value, name):
    if value.lower() in ("true", "1"):
        return True
    if value.lower() in ("false", "0"):
        return False
    raise ValidationError({name: ["Use true or false."]})


def apply_job_filters(queryset, params, allow_active_filter=False):
    """Filters a Job queryset using URL query parameters.

    title, location, company  : case-insensitive "contains"
    skills=python,sql         : jobs that require ALL listed skills (skills_match=any for ANY)
    job_type                  : exact (full_time, part_time, internship, contract, freelance)
    max_experience=1          : jobs asking for at most this many years
    is_active=true|false      : only for the recruiter's own list
    ordering                  : created_at, job_title, required_experience (prefix - for descending)
    """
    title = params.get("title", "").strip()
    if title:
        queryset = queryset.filter(job_title__icontains=title)

    location = params.get("location", "").strip()
    if location:
        queryset = queryset.filter(location__icontains=location)

    company = params.get("company", "").strip()
    if company:
        queryset = queryset.filter(company_name__icontains=company)

    job_type = params.get("job_type", "").strip()
    if job_type:
        if job_type not in Job.JobType.values:
            raise ValidationError({"job_type": [f"Choose one of: {', '.join(Job.JobType.values)}."]})
        queryset = queryset.filter(job_type=job_type)

    max_experience = params.get("max_experience", "").strip()
    if max_experience:
        if not max_experience.isdigit():
            raise ValidationError({"max_experience": ["Enter a whole number of years."]})
        queryset = queryset.filter(required_experience__lte=int(max_experience))

    skills = params.get("skills", "")
    names = [part.strip() for part in skills.split(",") if part.strip()]
    if names:
        if len(names) > MAX_SKILL_FILTERS:
            raise ValidationError({"skills": [f"Use at most {MAX_SKILL_FILTERS} skills."]})
        canonical = [canonical_skill(name)[0] for name in names]
        match = params.get("skills_match", "all").lower()
        if match not in ("all", "any"):
            raise ValidationError({"skills_match": ["Use all or any."]})
        if match == "any":
            condition = Q()
            for name in canonical:
                condition |= Q(required_skills__name__iexact=name)
            queryset = queryset.filter(condition)
        else:
            for name in canonical:  # one join per skill = the job must have every skill
                queryset = queryset.filter(required_skills__name__iexact=name)
        queryset = queryset.distinct()

    if allow_active_filter and params.get("is_active", "").strip():
        queryset = queryset.filter(is_active=_bool_param(params["is_active"].strip(), "is_active"))

    ordering = params.get("ordering", "").strip()
    if ordering:
        if ordering not in ALLOWED_ORDERING:
            raise ValidationError({"ordering": [f"Choose one of: {', '.join(sorted(ALLOWED_ORDERING))}."]})
        queryset = queryset.order_by(ordering, "-id")
    return queryset