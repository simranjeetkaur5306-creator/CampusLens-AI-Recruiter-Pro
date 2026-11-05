from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsRecruiter

from .models import Recruiter
from .serializers import RecruiterProfileSerializer


class RecruiterMeView(generics.RetrieveUpdateAPIView):
    """GET or PATCH the logged-in recruiter's own profile and company info."""

    serializer_class = RecruiterProfileSerializer
    permission_classes = [IsAuthenticated, IsRecruiter]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        profile, _ = Recruiter.objects.get_or_create(user=self.request.user)
        return profile