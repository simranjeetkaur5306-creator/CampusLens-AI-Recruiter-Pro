from django.urls import path

from .views import ApplyView, MyApplicationsView

urlpatterns = [
    path("", ApplyView.as_view()),
    path("me/", MyApplicationsView.as_view()),
]