from django.db import transaction
from rest_framework import serializers

from core.serializers import StrictWritableFieldsMixin
from matching.services.storage import embed_job_safely
from recruiters.models import Recruiter

from .models import Job
from .services import resolve_skills

MAX_SKILLS_PER_JOB = 30
# editing any of these changes what the job MEANS, so its embedding must be rebuilt
EMBEDDING_FIELDS = {"job_title", "description", "required_experience", "required_education"}


class SkillNamesField(serializers.ListField):
    """Accepts ["Python", "sql"] on input, returns ["Python", "SQL"] on output."""

    child = serializers.CharField(max_length=100, allow_blank=True)  # blanks are dropped below

    def to_representation(self, value):
        return [skill.name for skill in value.all()]

    def to_internal_value(self, data):
        names = super().to_internal_value(data)
        cleaned, seen = [], set()
        for name in names:
            name = " ".join(name.split())
            if name and name.lower() not in seen:
                seen.add(name.lower())
                cleaned.append(name)
        if len(cleaned) > MAX_SKILLS_PER_JOB:
            raise serializers.ValidationError(f"A job can have at most {MAX_SKILLS_PER_JOB} required skills.")
        return cleaned


class JobSerializer(StrictWritableFieldsMixin, serializers.ModelSerializer):
    required_skills = SkillNamesField(required=False)

    class Meta:
        model = Job
        fields = [
            "id", "job_title", "company_name", "location", "job_type", "description",
            "required_skills", "required_experience", "required_education",
            "salary_range", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "company_name": {"required": False, "allow_blank": True},
            "description": {"min_length": 30},
            "job_title": {"min_length": 3},
        }

    def validate(self, attrs):
        if "company_name" in attrs or self.instance is None:
            company = (attrs.get("company_name") or "").strip()
            if not company and self.instance is None:
                # fall back to the company name saved in the recruiter's profile
                request = self.context.get("request")
                company = (
                    Recruiter.objects.filter(user=request.user)
                    .values_list("company_name", flat=True)
                    .first()
                    or ""
                )
            if not company:
                raise serializers.ValidationError(
                    {"company_name": ["Required. Send it here or save it in your recruiter profile."]}
                )
            attrs["company_name"] = company
        return attrs

    def create(self, validated_data):
        skills = validated_data.pop("required_skills", [])
        with transaction.atomic():
            job = Job.objects.create(**validated_data)  # recruiter comes from serializer.save(recruiter=...)
            job.required_skills.set(resolve_skills(skills))
        embed_job_safely(job)  # never fails the request; `manage.py embed_all` can retry later
        return job

    def update(self, instance, validated_data):
        skills = validated_data.pop("required_skills", None)
        meaning_changed = skills is not None or bool(EMBEDDING_FIELDS & set(validated_data))
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            if skills is not None:
                instance.required_skills.set(resolve_skills(skills))
        if meaning_changed:
            embed_job_safely(instance)
        return instance