from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsCandidate

from .models import Candidate
from .serializers import CandidateProfileSerializer


class CandidateMeView(generics.RetrieveUpdateAPIView):
    """GET or PATCH the logged-in candidate's own profile."""

    serializer_class = CandidateProfileSerializer
    permission_classes = [IsAuthenticated, IsCandidate]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        # Normally created at registration; created here for older accounts.
        profile, _ = Candidate.objects.get_or_create(user=self.request.user)
        return profile