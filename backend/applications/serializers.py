from rest_framework import serializers

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