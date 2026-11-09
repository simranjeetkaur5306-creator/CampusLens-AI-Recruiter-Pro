from django.contrib import admin

from .models import Resume, Skill


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    search_fields = ("name",)


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "candidate", "parsing_status", "is_active", "uploaded_at")
    list_filter = ("parsing_status", "is_active", "file_type")
    search_fields = ("original_filename", "candidate__user__email")
    exclude = ("embedding",)
    readonly_fields = ("uploaded_at", "parsed_at", "embedding_model", "embedded_at")