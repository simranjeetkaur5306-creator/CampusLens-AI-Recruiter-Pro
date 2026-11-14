from rest_framework import serializers

from candidates.models import Candidate
from core.serializers import StrictWritableFieldsMixin
from jobs.models import Job

from .models import Application


class ApplicationCreateSerializer(StrictWritableFieldsMixin, serializers.Serializer):
    """Input for applying: only the job id. Status, candidate and resume are decided by the server."""

    job = serializers.PrimaryKeyRelatedField(
        queryset=Job.objects.filter(is_active=True),
        error_messages={
            "does_not_exist": "This job is not open for applications.",
            "incorrect_type": "Send the id of the job.",
            "required": "This field is required.",
        },
    )


class JobSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ["id", "job_title", "company_name", "location", "job_type", "is_active"]


class ApplicationSerializer(serializers.ModelSerializer):
    job = JobSummarySerializer(read_only=True)
    resume = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ["id", "status", "applied_at", "job", "resume"]

    def get_resume(self, obj):
        if obj.resume is None:
            return None  # the candidate deleted that resume after applying
        return {"id": obj.resume.id, "original_filename": obj.resume.original_filename}


# ---------------------------------------------------------------------------
# Recruiter side (Phase 14): applicants of the recruiter's own jobs
# ---------------------------------------------------------------------------
class ApplicationStatusSerializer(StrictWritableFieldsMixin, serializers.Serializer):
    """Input for changing an application's status. Only the status can be sent."""

    status = serializers.ChoiceField(choices=Application.Status.choices)

    def validate_status(self, value):
        if value == Application.Status.INTERVIEW_SCHEDULED:
            raise serializers.ValidationError(
                "This status is set when an interview is scheduled, which is not available yet."
            )
        return value


class CandidateSummarySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "id", "name", "email", "headline", "university", "degree",
            "graduation_year", "location", "linkedin_url", "github_url",
        ]

    def get_name(self, obj):
        user = obj.user
        return f"{user.first_name} {user.last_name}".strip() or user.email


class ReceivedApplicationSerializer(serializers.ModelSerializer):
    job = JobSummarySerializer(read_only=True)
    candidate = CandidateSummarySerializer(read_only=True)
    resume = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ["id", "status", "applied_at", "updated_at", "job", "candidate", "resume"]

    def get_resume(self, obj):
        resume = obj.resume
        if resume is None:
            return None
        return {
            "id": resume.id,
            "original_filename": resume.original_filename,
            "uploaded_at": resume.uploaded_at,
            "skills": [skill.name for skill in resume.skills.all()],
        }


class ReceivedApplicationDetailSerializer(ReceivedApplicationSerializer):
    """Adds the parsed resume details. The raw resume text is deliberately NOT included."""

    def get_resume(self, obj):
        resume = obj.resume
        if resume is None:
            return None
        return {
            "id": resume.id,
            "original_filename": resume.original_filename,
            "file_type": resume.file_type,
            "uploaded_at": resume.uploaded_at,
            "has_file": bool(resume.file),
            "contact": resume.contact,
            "skills": [{"name": skill.name, "category": skill.category} for skill in resume.skills.all()],
            "education": resume.education,
            "experience": resume.experience,
            "projects": resume.projects,
            "certifications": resume.certifications,
        }