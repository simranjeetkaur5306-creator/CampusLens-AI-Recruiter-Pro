from django.db import IntegrityError, transaction
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCandidate
from candidates.models import Candidate
from resumes.models import Resume

from .models import Application
from .serializers import ApplicationCreateSerializer, ApplicationSerializer

CANDIDATE_ONLY = [IsAuthenticated, IsCandidate]


class ApplyView(APIView):
    """POST /api/applications/  {"job": <id>}  Apply to an active job with your active resume."""

    permission_classes = CANDIDATE_ONLY

    def post(self, request):
        serializer = ApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.validated_data["job"]
        candidate, _ = Candidate.objects.get_or_create(user=request.user)

        resume = Resume.objects.filter(
            candidate=candidate, is_active=True, parsing_status=Resume.ParsingStatus.SUCCESS
        ).first()
        if resume is None:
            raise ValidationError({"resume": ["Upload a resume before applying to a job."]})

        already = ValidationError({"job": ["You have already applied to this job."]})
        if Application.objects.filter(candidate=candidate, job=job).exists():
            raise already
        try:
            with transaction.atomic():
                application = Application.objects.create(candidate=candidate, job=job, resume=resume)
        except IntegrityError:  # two requests at the same moment
            raise already

        return Response(
            {"message": "Application submitted.", "application": ApplicationSerializer(application).data},
            status=status.HTTP_201_CREATED,
        )


class MyApplicationsView(generics.ListAPIView):
    """GET /api/applications/me/  The logged-in candidate's applications, newest first."""

    serializer_class = ApplicationSerializer
    permission_classes = CANDIDATE_ONLY

    def get_queryset(self):
        return Application.objects.filter(candidate__user=self.request.user).select_related("job", "resume")