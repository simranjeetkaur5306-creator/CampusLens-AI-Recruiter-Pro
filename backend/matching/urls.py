from django.urls import path

from .views import JobSemanticSearchView

urlpatterns = [
    path("jobs/search/", JobSemanticSearchView.as_view()),
]