from django.contrib import admin

from .models import Recruiter


@admin.register(Recruiter)
class RecruiterAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "designation", "updated_at")
    search_fields = ("user__email", "company_name")