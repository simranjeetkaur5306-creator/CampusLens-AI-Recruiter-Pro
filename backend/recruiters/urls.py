from django.urls import path

from .views import RecruiterMeView

urlpatterns = [
    path("me/", RecruiterMeView.as_view()),
]