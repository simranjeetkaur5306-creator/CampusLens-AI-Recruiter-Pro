from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CandidateOnlyCheckView,
    CandidateRegisterView,
    LoginView,
    LogoutView,
    MeView,
    RecruiterOnlyCheckView,
    RecruiterRegisterView,
)

urlpatterns = [
    path("register/candidate/", CandidateRegisterView.as_view()),
    path("register/recruiter/", RecruiterRegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),
    # temporary role checks (removed in Phase 4)
    path("rbac-check/candidate/", CandidateOnlyCheckView.as_view()),
    path("rbac-check/recruiter/", RecruiterOnlyCheckView.as_view()),
]