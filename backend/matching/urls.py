from django.urls import path

from .views import JobRankingView, JobRecommendationsView, JobSemanticSearchView

urlpatterns = [
    path("jobs/search/", JobSemanticSearchView.as_view()),
    path("jobs/<int:job_id>/ranking/", JobRankingView.as_view()),
    path("recommendations/", JobRecommendationsView.as_view()),
]