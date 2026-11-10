from django.urls import path

from .views import JobSkillGapView

urlpatterns = [
    path("jobs/<int:job_id>/", JobSkillGapView.as_view()),
]