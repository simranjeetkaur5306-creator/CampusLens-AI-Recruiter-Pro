from rest_framework import serializers

from .models import Resume


class ResumeListSerializer(serializers.ModelSerializer):
    skills = serializers.SerializerMethodField()

    class Meta:
        model = Resume
        fields = [
            "id", "original_filename", "file_type", "file_size", "uploaded_at",
            "is_active", "parsing_status", "parsing_error", "skills",
        ]

    def get_skills(self, obj):
        return [skill.name for skill in obj.skills.all()]


class ResumeDetailSerializer(serializers.ModelSerializer):
    skills = serializers.SerializerMethodField()

    class Meta:
        model = Resume
        fields = [
            "id", "original_filename", "file_type", "file_size", "uploaded_at",
            "is_active", "parsing_status", "parsing_error", "parsed_at",
            "contact", "skills", "education", "experience", "projects",
            "certifications", "extracted_text",
        ]

    def get_skills(self, obj):
        return [{"name": skill.name, "category": skill.category} for skill in obj.skills.all()]


class ResumeUploadSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=False)