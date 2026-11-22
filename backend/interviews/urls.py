from django.urls import path

from .schedule_views import ApplicationInterviewsView, InterviewDetailView, InterviewListView
from .views import (
    ApplicationQuestionsView,
    CandidateJobQuestionsView,
    QuestionSetDetailView,
    QuestionSetListView,
)

urlpatterns = [
    # AI interview questions (Phase 11)
    path("jobs/<int:job_id>/questions/", CandidateJobQuestionsView.as_view()),
    path("applications/<int:application_id>/questions/", ApplicationQuestionsView.as_view()),
    path("questions/", QuestionSetListView.as_view()),
    path("questions/<int:pk>/", QuestionSetDetailView.as_view()),
    # Interview scheduling (Phase 16, recruiters)
    path("applications/<int:application_id>/schedule/", ApplicationInterviewsView.as_view()),
    path("schedule/", InterviewListView.as_view()),
    path("schedule/<int:pk>/", InterviewDetailView.as_view()),
]