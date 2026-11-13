from django.contrib import admin

from .models import InterviewQuestionSet


@admin.register(InterviewQuestionSet)
class InterviewQuestionSetAdmin(admin.ModelAdmin):
    list_display = ("id", "audience", "job", "candidate", "requested_by", "question_count", "model_name", "created_at")
    list_filter = ("audience", "model_name")
    readonly_fields = ("prompt_tokens", "completion_tokens", "created_at")
