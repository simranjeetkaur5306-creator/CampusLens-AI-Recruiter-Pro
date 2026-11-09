import uuid
from pathlib import Path

from django.db import models

from pgvector.django import HnswIndex, VectorField

from candidates.models import Candidate


def resume_upload_path(instance, filename):
    """Random file name inside a per-user folder (never trust the uploaded name)."""
    ext = Path(filename).suffix.lower()
    return f"resumes/{instance.candidate.user_id}/{uuid.uuid4().hex}{ext}"


class Skill(models.Model):
    """Master list of skills (shared by resumes now and job postings later)."""

    name = models.CharField(max_length=100, unique=True)  # e.g. "Machine Learning"
    category = models.CharField(max_length=50, blank=True)  # e.g. "AI/ML"

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Resume(models.Model):
    class FileType(models.TextChoices):
        PDF = "pdf", "PDF"
        DOCX = "docx", "DOCX"

    class ParsingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="resumes"
    )
    file = models.FileField(upload_to=resume_upload_path)
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FileType.choices)
    file_size = models.PositiveIntegerField(help_text="Size in bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)

    # Parsing result
    parsing_status = models.CharField(
        max_length=10, choices=ParsingStatus.choices, default=ParsingStatus.PENDING
    )
    parsing_error = models.TextField(blank=True)
    parsed_at = models.DateTimeField(null=True, blank=True)

    # Extracted information (nothing is invented; empty if not found)
    extracted_text = models.TextField(blank=True)
    contact = models.JSONField(default=dict, blank=True)  # name, email, phone, links
    education = models.JSONField(default=list, blank=True)
    experience = models.JSONField(default=list, blank=True)
    projects = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    skills = models.ManyToManyField(Skill, related_name="resumes", blank=True)

    # Semantic vector (Phase 8). 384 = output size of all-MiniLM-L6-v2; keep in sync with
    # settings.EMBEDDING_DIMENSIONS. NULL until the resume has been embedded.
    embedding = VectorField(dimensions=384, null=True, blank=True)
    embedding_model = models.CharField(max_length=100, blank=True)
    embedded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["candidate", "is_active"]),
            HnswIndex(
                name="resume_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]