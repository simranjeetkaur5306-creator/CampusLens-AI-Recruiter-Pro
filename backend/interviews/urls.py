from django.urls import path

from .views import (
    ApplicationQuestionsView,
    CandidateJobQuestionsView,
    QuestionSetDetailView,
    QuestionSetListView,
)

urlpatterns = [
    path("jobs/<int:job_id>/questions/", CandidateJobQuestionsView.as_view()),
    path("applications/<int:application_id>/questions/", ApplicationQuestionsView.as_view()),
    path("questions/", QuestionSetListView.as_view()),
    path("questions/<int:pk>/", QuestionSetDetailView.as_view()),
]
