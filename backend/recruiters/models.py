from django.conf import settings
from django.db import models

from core.validators import phone_validator


class Recruiter(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recruiter_profile",
    )
    company_name = models.CharField(max_length=150, blank=True)
    company_website = models.URLField(blank=True)
    company_location = models.CharField(max_length=100, blank=True)
    company_description = models.TextField(blank=True, max_length=2000)
    designation = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True, validators=[phone_validator])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Recruiter: {self.user.email}"