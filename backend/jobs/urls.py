from django.urls import path

from .views import (
    CandidateJobDetailView,
    CandidateJobListView,
    RecruiterJobDetailView,
    RecruiterJobListCreateView,
)

urlpatterns = [
    # candidates (read-only, active jobs)
    path("", CandidateJobListView.as_view()),
    path("<int:pk>/", CandidateJobDetailView.as_view()),
    # recruiters (own jobs)
    path("manage/", RecruiterJobListCreateView.as_view()),
    path("manage/<int:pk>/", RecruiterJobDetailView.as_view()),
]