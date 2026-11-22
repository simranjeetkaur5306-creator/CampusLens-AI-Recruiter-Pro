from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from django.utils import timezone
from rest_framework import serializers

from core.serializers import StrictWritableFieldsMixin

from .models import Interview

MAX_DAYS_AHEAD = 365
_link_validator = URLValidator(schemes=["http", "https"])


def future_error(moment):
    """Message if `moment` is not a sensible interview time, otherwise None."""
    now = timezone.now()
    if moment <= now:
        return "Choose a date and time in the future."
    if moment > now + timedelta(days=MAX_DAYS_AHEAD):
        return "Choose a date within the next year."
    return None


def clean_location(mode, location):
    """Online interviews need a real http(s) link; in-person ones need an address."""
    location = (location or "").strip()
    if mode == Interview.Mode.ONLINE:
        try:
            _link_validator(location)
        except DjangoValidationError:
            raise serializers.ValidationError(
                {"location": ["For an online interview, enter a meeting link that starts with http:// or https://."]}
            )
    elif mode == Interview.Mode.IN_PERSON and len(location) < 3:
        raise serializers.ValidationError({"location": ["For an in-person interview, enter the address."]})
    return location


class InterviewCreateSerializer(StrictWritableFieldsMixin, serializers.Serializer):
    """Input for scheduling. The application, status and creator are decided by the server."""

    scheduled_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(min_value=5, max_value=480, required=False, default=30)
    mode = serializers.ChoiceField(choices=Interview.Mode.choices)
    location = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    details = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")

    def validate_scheduled_at(self, value):
        message = future_error(value)
        if message:
            raise serializers.ValidationError(message)
        return value

    def validate(self, attrs):
        attrs["location"] = clean_location(attrs["mode"], attrs.get("location"))
        attrs["details"] = attrs.get("details", "").strip()
        return attrs


class InterviewUpdateSerializer(StrictWritableFieldsMixin, serializers.Serializer):
    """Input for editing. Needs context={"interview": <the interview being edited>}."""

    scheduled_at = serializers.DateTimeField(required=False)
    duration_minutes = serializers.IntegerField(min_value=5, max_value=480, required=False)
    mode = serializers.ChoiceField(choices=Interview.Mode.choices, required=False)
    location = serializers.CharField(max_length=500, required=False, allow_blank=True)
    details = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Interview.Status.choices, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Send at least one field to change.")
        interview = self.context["interview"]
        status = attrs.get("status", Interview.Status.SCHEDULED)

        if status == Interview.Status.SCHEDULED:
            if "scheduled_at" in attrs:
                message = future_error(attrs["scheduled_at"])
                if message:
                    raise serializers.ValidationError({"scheduled_at": [message]})
            if "mode" in attrs or "location" in attrs:
                mode = attrs.get("mode", interview.mode)
                attrs["location"] = clean_location(mode, attrs.get("location", interview.location))
        if "details" in attrs:
            attrs["details"] = attrs["details"].strip()
        return attrs


class InterviewSerializer(serializers.ModelSerializer):
    """What a recruiter sees. Needs application, job and candidate user loaded (select_related)."""

    application = serializers.SerializerMethodField()

    class Meta:
        model = Interview
        fields = [
            "id", "status", "scheduled_at", "duration_minutes", "mode", "location", "details",
            "created_at", "updated_at", "application",
        ]

    def get_application(self, obj):
        application = obj.application
        user = application.candidate.user
        return {
            "id": application.id,
            "status": application.status,
            "job": {
                "id": application.job_id,
                "job_title": application.job.job_title,
                "company_name": application.job.company_name,
            },
            "candidate": {
                "id": application.candidate_id,
                "name": f"{user.first_name} {user.last_name}".strip() or user.email,
                "email": user.email,
            },
        }