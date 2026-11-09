from django.contrib import admin

from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("job_title", "company_name", "location", "job_type", "is_active", "created_at")
    list_filter = ("is_active", "job_type")
    search_fields = ("job_title", "company_name", "location")
    filter_horizontal = ("required_skills",)
    exclude = ("embedding",)
    readonly_fields = ("embedding_model", "embedded_at")