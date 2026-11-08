from django.core.validators import MaxValueValidator
from django.db import models

from recruiters.models import Recruiter
from resumes.models import Skill


class Job(models.Model):
    """A job description posted by a recruiter (the JobDescription entity of the synopsis)."""

    class JobType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        INTERNSHIP = "internship", "Internship"
        CONTRACT = "contract", "Contract"
        FREELANCE = "freelance", "Freelance"

    recruiter = models.ForeignKey(Recruiter, on_delete=models.CASCADE, related_name="jobs")
    job_title = models.CharField(max_length=200)
    company_name = models.CharField(max_length=150)
    location = models.CharField(max_length=100)
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    description = models.TextField()
    required_skills = models.ManyToManyField(Skill, related_name="jobs", blank=True)
    required_experience = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(40)],
        help_text="Minimum years of experience (0 = freshers welcome)",
    )
    required_education = models.CharField(max_length=150, blank=True)
    salary_range = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True, help_text="Published (visible to candidates)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # The embedding vector column is added in Phase 7.

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["is_active", "-created_at"])]

    def __str__(self):
        return f"{self.job_title} at {self.company_name}"