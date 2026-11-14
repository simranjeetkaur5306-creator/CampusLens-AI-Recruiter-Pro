from django.urls import path

from .views import (
    ApplicationResumeFileView,
    ApplicationStatusView,
    ApplyView,
    MyApplicationsView,
    ReceivedApplicationDetailView,
    ReceivedApplicationsView,
)

urlpatterns = [
    # candidates
    path("", ApplyView.as_view()),
    path("me/", MyApplicationsView.as_view()),
    # recruiters (own jobs only)
    path("received/", ReceivedApplicationsView.as_view()),
    path("<int:pk>/", ReceivedApplicationDetailView.as_view()),
    path("<int:pk>/status/", ApplicationStatusView.as_view()),
    path("<int:pk>/resume-file/", ApplicationResumeFileView.as_view()),
]