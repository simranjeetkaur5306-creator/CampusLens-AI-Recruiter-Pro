from django.urls import path

from .views import CandidateMeView

urlpatterns = [
    path("me/", CandidateMeView.as_view()),
]