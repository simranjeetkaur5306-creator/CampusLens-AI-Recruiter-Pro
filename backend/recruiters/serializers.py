from rest_framework import serializers

from core.serializers import StrictWritableFieldsMixin

from .models import Recruiter


class RecruiterProfileSerializer(StrictWritableFieldsMixin, serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = Recruiter
        fields = [
            "id", "email", "first_name", "last_name",
            "company_name", "company_website", "company_location",
            "company_description", "designation", "phone",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]