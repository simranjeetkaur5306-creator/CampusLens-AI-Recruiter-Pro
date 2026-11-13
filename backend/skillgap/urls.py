from django.urls import path

from .views import JobSkillGapAISummaryView, JobSkillGapView

urlpatterns = [
    path("jobs/<int:job_id>/", JobSkillGapView.as_view()),
    path("jobs/<int:job_id>/ai-summary/", JobSkillGapAISummaryView.as_view()),
]