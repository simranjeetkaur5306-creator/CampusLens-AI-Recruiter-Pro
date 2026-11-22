from django.urls import path

from .views import RecruiterOverviewView

urlpatterns = [
    path("recruiter/overview/", RecruiterOverviewView.as_view()),
]