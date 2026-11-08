from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsCandidate, IsRecruiter
from recruiters.models import Recruiter

from .filters import apply_job_filters
from .models import Job
from .serializers import JobSerializer

CANDIDATE_ONLY = [IsAuthenticated, IsCandidate]
RECRUITER_ONLY = [IsAuthenticated, IsRecruiter]


def with_skills(queryset):
    return queryset.prefetch_related("required_skills")


# ---------------- Candidates: read-only access to ACTIVE jobs ----------------
class CandidateJobListView(generics.ListAPIView):
    serializer_class = JobSerializer
    permission_classes = CANDIDATE_ONLY

    def get_queryset(self):
        queryset = with_skills(Job.objects.filter(is_active=True))
        return apply_job_filters(queryset, self.request.query_params)


class CandidateJobDetailView(generics.RetrieveAPIView):
    serializer_class = JobSerializer
    permission_classes = CANDIDATE_ONLY

    def get_queryset(self):
        return with_skills(Job.objects.filter(is_active=True))  # inactive jobs give 404


# ---------------- Recruiters: manage their OWN jobs ----------------
class RecruiterJobListCreateView(generics.ListCreateAPIView):
    serializer_class = JobSerializer
    permission_classes = RECRUITER_ONLY

    def get_queryset(self):
        queryset = with_skills(Job.objects.filter(recruiter__user=self.request.user))
        return apply_job_filters(queryset, self.request.query_params, allow_active_filter=True)

    def perform_create(self, serializer):
        recruiter, _ = Recruiter.objects.get_or_create(user=self.request.user)
        serializer.save(recruiter=recruiter)  # the owner is always the logged-in recruiter


class RecruiterJobDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = JobSerializer
    permission_classes = RECRUITER_ONLY
    http_method_names = ["get", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        # another recruiter's job id gives 404, so its existence is not revealed
        return with_skills(Job.objects.filter(recruiter__user=self.request.user))

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response({"message": "Job deleted."}, status=status.HTTP_200_OK)