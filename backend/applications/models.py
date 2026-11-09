from django.db import models

from candidates.models import Candidate
from jobs.models import Job
from resumes.models import Resume


class Application(models.Model):
    """A candidate's application to one job, made with the resume that was active at that moment."""

    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        SHORTLISTED = "shortlisted", "Shortlisted"
        REJECTED = "rejected", "Rejected"
        INTERVIEW_SCHEDULED = "interview_scheduled", "Interview scheduled"

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="applications")
    # PROTECT: a job that has applications cannot be deleted by accident (unpublish it instead)
    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name="applications")
    # SET_NULL: a candidate may delete a resume later; the application itself is kept
    resume = models.ForeignKey(Resume, on_delete=models.SET_NULL, null=True, blank=True, related_name="applications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-applied_at"]
        constraints = [
            models.UniqueConstraint(fields=["candidate", "job"], name="unique_application_per_job"),
        ]
        indexes = [models.Index(fields=["job", "status"])]

    def __str__(self):
        return f"{self.candidate.user.email} -> {self.job.job_title} ({self.status})"