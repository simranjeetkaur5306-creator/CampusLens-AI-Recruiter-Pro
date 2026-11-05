from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.validators import phone_validator


class Candidate(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="candidate_profile",
    )
    phone = models.CharField(max_length=20, blank=True, validators=[phone_validator])
    headline = models.CharField(max_length=150, blank=True)
    location = models.CharField(max_length=100, blank=True)
    university = models.CharField(max_length=150, blank=True)
    degree = models.CharField(max_length=100, blank=True)
    graduation_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1990), MaxValueValidator(2100)],
    )
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    bio = models.TextField(blank=True, max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Candidate: {self.user.email}"