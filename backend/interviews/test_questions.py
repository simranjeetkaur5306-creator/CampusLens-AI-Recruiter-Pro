from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.permissions import IsCandidate, IsRecruiter
from applications.models import Application
from candidates.models import Candidate
from core.llm import AIUnavailable, LLMError
from jobs.models import Job
from resumes.models import Resume

from .models import InterviewQuestionSet
from .serializers import InterviewQuestionSetSerializer
from .services import questions as question_service


def generate_and_save(*, job, resume, audience, requested_by, candidate=None, application=None):
    try:
        questions, result = question_service.generate(job, resume, audience)
    except LLMError as error:
        raise AIUnavailable(error)
    return InterviewQuestionSet.objects.create(
        job=job,
        candidate=candidate,
        application=application,
        resume=resume,
        requested_by=requested_by,
        audience=audience,
        used_resume=resume is not None,
        questions=questions,
        question_count=sum(len(rows) for rows in questions.values()),
        model_name=result.model,
        prompt_version=question_service.PROMPT_VERSION,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
    )


class AIThrottleMixin:
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"  # settings: REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["ai"]


class CandidateJobQuestionsView(AIThrottleMixin, APIView):
    """POST /api/interviews/jobs/<job_id>/questions/   (candidate)

    Practice questions for one job, tailored to the candidate's ACTIVE resume. The job must be
    open, or the candidate must already have applied to it (same rule as the skill-gap analysis).
    """

    permission_classes = [IsAuthenticated, IsCandidate]

    def post(self, request, job_id):
        candidate, _ = Candidate.objects.get_or_create(user=request.user)
        visible = (
            Job.objects.filter(Q(is_active=True) | Q(applications__candidate=candidate))
            .distinct()
            .prefetch_related("required_skills")
        )
        job = get_object_or_404(visible, pk=job_id)
        resume = (
            Resume.objects.filter(candidate=candidate, is_active=True, parsing_status=Resume.ParsingStatus.SUCCESS)
            .prefetch_related("skills")
            .first()
        )
        if resume is None:
            raise ValidationError({"resume": ["Upload a resume to get interview questions tailored to you."]})

        question_set = generate_and_save(
            job=job,
            resume=resume,
            audience=InterviewQuestionSet.Audience.CANDIDATE,
            requested_by=request.user,
            candidate=candidate,
        )
        return Response(InterviewQuestionSetSerializer(question_set).data, status=status.HTTP_201_CREATED)


class ApplicationQuestionsView(AIThrottleMixin, APIView):
    """POST /api/interviews/applications/<application_id>/questions/   (recruiter, own jobs only)

    Interview questions for one applicant, based on the job and the resume they applied with.
    """

    permission_classes = [IsAuthenticated, IsRecruiter]

    def post(self, request, application_id):
        applications = Application.objects.filter(job__recruiter__user=request.user).select_related(
            "job", "candidate__user", "resume"
        )
        application = get_object_or_404(applications, pk=application_id)  # someone else's gives 404
        resume = application.resume
        if resume is not None and resume.parsing_status != Resume.ParsingStatus.SUCCESS:
            resume = None  # nothing reliable to tailor to; the questions are based on the job only

        question_set = generate_and_save(
            job=application.job,
            resume=resume,
            audience=InterviewQuestionSet.Audience.RECRUITER,
            requested_by=request.user,
            candidate=application.candidate,
            application=application,
        )
        return Response(InterviewQuestionSetSerializer(question_set).data, status=status.HTTP_201_CREATED)


class MyQuestionSetsMixin:
    """Every user sees only the question sets they generated themselves."""

    serializer_class = InterviewQuestionSetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InterviewQuestionSet.objects.filter(requested_by=self.request.user).select_related(
            "job", "candidate__user"
        )


class QuestionSetListView(MyQuestionSetsMixin, generics.ListAPIView):
    """GET /api/interviews/questions/   newest first. Filters: ?job=<id>, ?application=<id>"""

    def get_queryset(self):
        queryset = super().get_queryset()
        for name in ("job", "application"):
            raw = self.request.query_params.get(name)
            if raw is not None:
                if not raw.strip().isdigit():
                    raise ValidationError({name: ["Use a whole number id."]})
                queryset = queryset.filter(**{f"{name}_id": int(raw)})
        return queryset


class QuestionSetDetailView(MyQuestionSetsMixin, generics.RetrieveDestroyAPIView):
    """GET / DELETE /api/interviews/questions/<id>/"""
