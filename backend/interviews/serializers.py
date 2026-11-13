from rest_framework import serializers

from .models import InterviewQuestionSet
from .services.questions import CATEGORY_LABELS, NOTE


class InterviewQuestionSetSerializer(serializers.ModelSerializer):
    job = serializers.SerializerMethodField()
    candidate_name = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    note = serializers.SerializerMethodField()

    class Meta:
        model = InterviewQuestionSet
        fields = [
            "id", "audience", "job", "application", "resume", "used_resume", "candidate_name",
            "question_count", "categories", "questions", "model_name", "prompt_version", "created_at", "note",
        ]
        read_only_fields = fields

    def get_job(self, obj):
        return {"id": obj.job_id, "job_title": obj.job.job_title, "company_name": obj.job.company_name}

    def get_candidate_name(self, obj):
        if obj.candidate is None:
            return None
        user = obj.candidate.user
        return f"{user.first_name} {user.last_name}".strip() or user.email

    def get_categories(self, obj):
        return CATEGORY_LABELS  # display names for the frontend tabs, in order

    def get_note(self, obj):
        return NOTE
