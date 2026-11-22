from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsRecruiter
from applications.models import Application
from notifications import services as notifications

from .models import Interview
from .schedule_serializers import InterviewCreateSerializer, InterviewSerializer, InterviewUpdateSerializer

RECRUITER_ONLY = [IsAuthenticated, IsRecruiter]
CONTENT_FIELDS = ("scheduled_at", "duration_minutes", "mode", "location", "details")


def own_applications(user):
    """Applications to the recruiter's OWN jobs. Anyone else's id gives 404."""
    return Application.objects.filter(job__recruiter__user=user).select_related("job", "candidate__user")


def own_interviews(user):
    return Interview.objects.filter(application__job__recruiter__user=user).select_related(
        "application__job", "application__candidate__user"
    )


def with_email(interview, email_status):
    payload = dict(InterviewSerializer(interview).data)
    payload["email"] = {"status": email_status, "recipient": "candidate"}
    return payload


class ApplicationInterviewsView(APIView):
    """/api/interviews/applications/<application_id>/schedule/   (recruiter, own jobs only)

    GET  -> every interview of this application
    POST -> schedule an interview. The application's status becomes "interview_scheduled" and the
            candidate is emailed (the response says whether the email was really sent).
    """

    permission_classes = RECRUITER_ONLY

    def get(self, request, application_id):
        application = get_object_or_404(own_applications(request.user), pk=application_id)
        interviews = own_interviews(request.user).filter(application=application)
        return Response(InterviewSerializer(interviews, many=True).data)

    def post(self, request, application_id):
        serializer = InterviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            application = get_object_or_404(
                own_applications(request.user).select_for_update(of=("self",)), pk=application_id
            )
            if application.status == Application.Status.REJECTED:
                raise ValidationError(
                    {"application": ["This application was rejected. Change its status before scheduling an interview."]}
                )
            if application.interviews.filter(status=Interview.Status.SCHEDULED).exists():
                raise ValidationError(
                    {"application": ["This application already has a scheduled interview. Edit or cancel it first."]}
                )
            interview = Interview.objects.create(
                application=application, created_by=request.user, **serializer.validated_data
            )
            if application.status != Application.Status.INTERVIEW_SCHEDULED:
                application.status = Application.Status.INTERVIEW_SCHEDULED
                application.save(update_fields=["status", "updated_at"])

        email_status = notifications.interview_scheduled(interview)
        return Response(with_email(interview, email_status), status=status.HTTP_201_CREATED)


class InterviewListView(generics.ListAPIView):
    """GET /api/interviews/schedule/?status=scheduled|completed|cancelled&application=<id>   (recruiter)"""

    serializer_class = InterviewSerializer
    permission_classes = RECRUITER_ONLY

    def get_queryset(self):
        queryset = own_interviews(self.request.user)
        params = self.request.query_params

        status_value = params.get("status")
        if status_value is not None:
            if status_value not in Interview.Status.values:
                raise ValidationError({"status": [f"Choose one of: {', '.join(Interview.Status.values)}."]})
            queryset = queryset.filter(status=status_value)

        application = params.get("application")
        if application is not None:
            if not application.strip().isdigit():
                raise ValidationError({"application": ["Use a whole number id."]})
            queryset = queryset.filter(application_id=int(application))
        return queryset


class InterviewDetailView(APIView):
    """/api/interviews/schedule/<id>/   (recruiter, own jobs only)

    GET   -> one interview
    PATCH -> change time/mode/location/details, or set status to "completed" or "cancelled".
             Only a scheduled interview can be changed. Cancelling the only scheduled interview puts
             the application back to "shortlisted". Changes the candidate must know about are emailed.
    """

    permission_classes = RECRUITER_ONLY
    http_method_names = ["get", "patch", "options"]

    def get(self, request, pk):
        interview = get_object_or_404(own_interviews(request.user), pk=pk)
        return Response(InterviewSerializer(interview).data)

    def patch(self, request, pk):
        interview = get_object_or_404(own_interviews(request.user), pk=pk)
        serializer = InterviewUpdateSerializer(data=request.data, context={"interview": interview})
        serializer.is_valid(raise_exception=True)
        changes = dict(serializer.validated_data)
        new_status = changes.pop("status", Interview.Status.SCHEDULED)

        with transaction.atomic():
            interview = (
                Interview.objects.select_for_update(of=("self",))
                .select_related("application__job", "application__candidate__user")
                .get(pk=interview.pk)
            )
            if interview.status != Interview.Status.SCHEDULED:
                raise ValidationError({"status": ["Only a scheduled interview can be changed."]})

            content_changed = False
            if new_status == Interview.Status.SCHEDULED:
                for field in CONTENT_FIELDS:
                    if field in changes and getattr(interview, field) != changes[field]:
                        setattr(interview, field, changes[field])
                        content_changed = True
            elif new_status == Interview.Status.COMPLETED and interview.scheduled_at > timezone.now():
                raise ValidationError({"status": ["An interview can be marked completed only after it has started."]})

            interview.status = new_status
            interview.save()

            application = interview.application
            if (
                new_status == Interview.Status.CANCELLED
                and application.status == Application.Status.INTERVIEW_SCHEDULED
                and not application.interviews.filter(status=Interview.Status.SCHEDULED).exists()
            ):
                application.status = Application.Status.SHORTLISTED
                application.save(update_fields=["status", "updated_at"])

        if new_status == Interview.Status.CANCELLED:
            email_status = notifications.interview_cancelled(interview)
        elif new_status == Interview.Status.SCHEDULED and content_changed:
            email_status = notifications.interview_updated(interview)
        else:
            email_status = None
        if email_status is None:
            return Response(InterviewSerializer(interview).data)
        return Response(with_email(interview, email_status))