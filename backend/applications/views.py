from django.db import IntegrityError, transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils.http import content_disposition_header
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCandidate, IsRecruiter
from candidates.models import Candidate
from resumes.models import Resume

from .models import Application
from .serializers import (
    ApplicationCreateSerializer,
    ApplicationSerializer,
    ApplicationStatusSerializer,
    ReceivedApplicationDetailSerializer,
    ReceivedApplicationSerializer,
)

CANDIDATE_ONLY = [IsAuthenticated, IsCandidate]
RECRUITER_ONLY = [IsAuthenticated, IsRecruiter]


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


# ---------------------------------------------------------------------------
# Recruiter side (Phase 14)
# ---------------------------------------------------------------------------
def received_applications(user):
    """Applications to the logged-in recruiter's OWN jobs. This is the ownership check:
    another recruiter's application id simply gives 404."""
    return (
        Application.objects.filter(job__recruiter__user=user)
        .select_related("job", "candidate__user", "resume")
        .prefetch_related("resume__skills")
    )


class ReceivedApplicationsView(generics.ListAPIView):
    """GET /api/applications/received/   (recruiter)

    Applicants of the recruiter's own jobs, newest first.
    Filters: ?job=<id>  ?status=applied|shortlisted|rejected|interview_scheduled
    """

    serializer_class = ReceivedApplicationSerializer
    permission_classes = RECRUITER_ONLY

    def get_queryset(self):
        queryset = received_applications(self.request.user)
        params = self.request.query_params

        job = params.get("job")
        if job is not None:
            if not job.strip().isdigit():
                raise ValidationError({"job": ["Use a whole number id."]})
            queryset = queryset.filter(job_id=int(job))

        status_value = params.get("status")
        if status_value is not None:
            if status_value not in Application.Status.values:
                raise ValidationError({"status": [f"Choose one of: {', '.join(Application.Status.values)}."]})
            queryset = queryset.filter(status=status_value)
        return queryset


class ReceivedApplicationDetailView(generics.RetrieveAPIView):
    """GET /api/applications/<id>/   (recruiter, own jobs only)  Candidate profile + parsed resume."""

    serializer_class = ReceivedApplicationDetailSerializer
    permission_classes = RECRUITER_ONLY

    def get_queryset(self):
        return received_applications(self.request.user)


class ApplicationStatusView(APIView):
    """PATCH /api/applications/<id>/status/  {"status": "shortlisted" | "rejected" | "applied"}

    The recruiter decides; nothing here is automatic. "interview_scheduled" is not accepted
    because it will be set by interview scheduling (Phase 16).
    """

    permission_classes = RECRUITER_ONLY
    http_method_names = ["patch", "options"]

    def patch(self, request, pk):
        application = get_object_or_404(received_applications(request.user), pk=pk)
        serializer = ApplicationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        if application.status != new_status:
            application.status = new_status
            application.save(update_fields=["status", "updated_at"])
        return Response(ReceivedApplicationSerializer(application).data)


class ApplicationResumeFileView(APIView):
    """GET /api/applications/<id>/resume-file/   (recruiter, own jobs only)

    Streams the resume file the candidate applied with. Files are never served from a public URL;
    this view is the only way to read them, and it checks that the application belongs to the
    recruiter first.
    """

    permission_classes = RECRUITER_ONLY
    CONTENT_TYPES = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    def get(self, request, pk):
        application = get_object_or_404(received_applications(request.user), pk=pk)
        resume = application.resume
        if resume is None or not resume.file:
            raise NotFound("This application has no resume file.")
        try:
            handle = resume.file.open("rb")
        except (FileNotFoundError, ValueError, OSError):
            raise NotFound("The resume file is no longer available.")

        response = FileResponse(handle, content_type=self.CONTENT_TYPES.get(resume.file_type, "application/octet-stream"))
        response["Content-Disposition"] = content_disposition_header(False, resume.original_filename)
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response