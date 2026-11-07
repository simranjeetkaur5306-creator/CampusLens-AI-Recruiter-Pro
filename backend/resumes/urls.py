from django.urls import path

from .views import (
    ActiveResumeView,
    ResumeActivateView,
    ResumeDetailView,
    ResumeListView,
    ResumeUploadView,
)

urlpatterns = [
    path("", ResumeListView.as_view()),
    path("upload/", ResumeUploadView.as_view()),
    path("me/", ActiveResumeView.as_view()),
    path("<int:pk>/", ResumeDetailView.as_view()),
    path("<int:pk>/activate/", ResumeActivateView.as_view()),
]