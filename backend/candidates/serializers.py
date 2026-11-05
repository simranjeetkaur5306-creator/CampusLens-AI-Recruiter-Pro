from rest_framework import serializers

from core.serializers import StrictWritableFieldsMixin

from .models import Candidate


class CandidateProfileSerializer(StrictWritableFieldsMixin, serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "id", "email", "first_name", "last_name",
            "phone", "headline", "location", "university", "degree",
            "graduation_year", "linkedin_url", "github_url", "bio",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]