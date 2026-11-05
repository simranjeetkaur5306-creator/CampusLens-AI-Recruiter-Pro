from django.contrib import admin

from .models import Candidate


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("user", "university", "graduation_year", "updated_at")
    search_fields = ("user__email", "university")