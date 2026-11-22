from django.db import IntegrityError, transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.http import content_disposition_header
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCandidate, IsRecruiter
from candidates.models import Candidate
from interviews.models import Interview
from notifications import services as notifications
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

        # Emails never block or undo the application; the response tells the truth about delivery.
        confirmation = notifications.application_received(application)
        notifications.new_application_for_recruiter(application)

        return Response(
            {
                "message": "Application submitted.",
                "application": ApplicationSerializer(application).data,
                "email": {"status": confirmation, "recipient": "you"},
            },
            status=status.HTTP_201_CREATED,
        )


class MyApplicationsView(generics.ListAPIView):
    """GET /api/applications/me/  The logged-in candidate's applications, newest first."""

    serializer_class = ApplicationSerializer
    permission_classes = CANDIDATE_ONLY

    def get_queryset(self):
        return (
            Application.objects.filter(candidate__user=self.request.user)
            .select_related("job", "resume")
            .prefetch_related("interviews")
        )


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

    The recruiter decides; nothing here is automatic.
    * "interview_scheduled" cannot be chosen here; scheduling an interview sets it.
    * While an interview is scheduled, only "rejected" is possible (it cancels that interview).
      To go back to "shortlisted", cancel the interview first.
    * Shortlisting and rejecting email the candidate; the response says whether the email was sent.
    """

    permission_classes = RECRUITER_ONLY
    http_method_names = ["patch", "options"]

    def patch(self, request, pk):
        application = get_object_or_404(received_applications(request.user), pk=pk)
        serializer = ApplicationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]

        email_status = None
        if application.status != new_status:
            cancelled = 0
            with transaction.atomic():
                scheduled = application.interviews.filter(status=Interview.Status.SCHEDULED)
                if scheduled.exists():
                    if new_status != Application.Status.REJECTED:
                        raise ValidationError(
                            {"status": ["This application has a scheduled interview. Cancel the interview first, or reject the application."]}
                        )
                    cancelled = scheduled.update(status=Interview.Status.CANCELLED, updated_at=timezone.now())
                application.status = new_status
                application.save(update_fields=["status", "updated_at"])

            if new_status == Application.Status.SHORTLISTED:
                email_status = notifications.application_shortlisted(application)
            elif new_status == Application.Status.REJECTED:
                email_status = notifications.application_rejected(application, interviews_cancelled=cancelled)

        payload = dict(ReceivedApplicationSerializer(application).data)
        if email_status is not None:
            payload["email"] = {"status": email_status, "recipient": "candidate"}
        return Response(payload)


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