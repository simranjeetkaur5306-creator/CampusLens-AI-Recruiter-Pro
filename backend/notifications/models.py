from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from applications.models import Application
from candidates.models import Candidate
from jobs.models import Job
from resumes.models import Resume


class InterviewQuestionSet(models.Model):
    """One set of AI-generated interview questions (Phase 11).

    Candidates generate practice sets for a job; recruiters generate interview sets for one of
    their applicants. Interview scheduling (date, time, mode) is the separate Interview model below.
    """

    class Audience(models.TextChoices):
        CANDIDATE = "candidate", "Candidate practice"
        RECRUITER = "recruiter", "Recruiter interview"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="question_sets")
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, null=True, blank=True, related_name="question_sets"
    )
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, null=True, blank=True, related_name="question_sets"
    )
    # SET_NULL: the questions stay readable if the candidate deletes that resume later
    resume = models.ForeignKey(Resume, on_delete=models.SET_NULL, null=True, blank=True, related_name="question_sets")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interview_question_sets"
    )
    audience = models.CharField(max_length=20, choices=Audience.choices)
    used_resume = models.BooleanField(default=False)

    # {"technical": [{"question", "skill", "difficulty", "answer_guide"}, ...], "conceptual": [...], ...}
    questions = models.JSONField()
    question_count = models.PositiveSmallIntegerField(default=0)

    # Which model and prompt produced it, and what it cost in tokens (for transparency and testing)
    model_name = models.CharField(max_length=100)
    prompt_version = models.CharField(max_length=20)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["requested_by", "-created_at"])]

    def __str__(self):
        return f"{self.get_audience_display()} questions for {self.job.job_title} ({self.created_at:%Y-%m-%d})"


class Interview(models.Model):
    """One scheduled interview for an application (Phase 16).

    An application can have several interviews over time (for example two rounds), but only ONE can
    be "scheduled" at a time. Reschedule by editing it; start another round after completing or
    cancelling the previous one.
    """

    class Mode(models.TextChoices):
        ONLINE = "online", "Online (video call)"
        IN_PERSON = "in_person", "In person"
        PHONE = "phone", "Phone call"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="interviews")
    scheduled_at = models.DateTimeField()  # date and time together, stored in UTC
    duration_minutes = models.PositiveSmallIntegerField(
        default=30, validators=[MinValueValidator(5), MaxValueValidator(480)]
    )
    mode = models.CharField(max_length=20, choices=Mode.choices)
    location = models.CharField(max_length=500, blank=True)  # meeting link, address or phone instructions
    details = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="scheduled_interviews"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_at"]
        indexes = [
            models.Index(fields=["application", "status"]),
            models.Index(fields=["scheduled_at"]),
        ]

    def __str__(self):
        return f"{self.get_mode_display()} interview for application {self.application_id} at {self.scheduled_at:%Y-%m-%d %H:%M}"