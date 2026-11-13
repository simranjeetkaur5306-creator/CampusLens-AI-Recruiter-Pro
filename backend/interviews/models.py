from django.conf import settings
from django.db import models

from applications.models import Application
from candidates.models import Candidate
from jobs.models import Job
from resumes.models import Resume


class InterviewQuestionSet(models.Model):
    """One set of AI-generated interview questions (Phase 11).

    Candidates generate practice sets for a job; recruiters generate interview sets for one of
    their applicants. Interview scheduling (date, time, mode) is a separate model in Phase 16.
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
