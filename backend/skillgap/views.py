from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.permissions import IsCandidate
from candidates.models import Candidate
from core.llm import AIUnavailable, LLMError
from jobs.models import Job
from resumes.models import Resume

from .services import ai_summary, analysis


class JobSkillGapView(APIView):
    """GET /api/skill-gap/jobs/<job_id>/   (candidate)

    Compares the skills on the candidate's ACTIVE resume with the skills the job requires.
    Optional: ?resume_id=<id> to analyse another of the candidate's own resumes.
    The job must be open, or the candidate must already have applied to it.
    """

    permission_classes = [IsAuthenticated, IsCandidate]

    def get(self, request, job_id):
        job, resume, result = self.analyse(request, job_id)
        return Response({**self.header(job, resume), **result})

    def analyse(self, request, job_id):
        """Returns (job, resume, analysis result) for the logged-in candidate."""
        candidate, _ = Candidate.objects.get_or_create(user=request.user)
        visible = (
            Job.objects.filter(Q(is_active=True) | Q(applications__candidate=candidate))
            .distinct()
            .prefetch_related("required_skills")
        )
        job = get_object_or_404(visible, pk=job_id)
        resume = self.pick_resume(request, candidate)

        result = analysis.analyze(
            resume_skills=[skill.name for skill in resume.skills.all()],
            resume_text=resume.extracted_text,
            job_skills=[{"name": skill.name, "category": skill.category} for skill in job.required_skills.all()],
        )
        return job, resume, result

    @staticmethod
    def header(job, resume):
        return {
            "job": {"id": job.id, "job_title": job.job_title, "company_name": job.company_name},
            "resume": {"id": resume.id, "original_filename": resume.original_filename, "is_active": resume.is_active},
        }

    def pick_resume(self, request, candidate):
        resumes = Resume.objects.filter(candidate=candidate).prefetch_related("skills")
        raw = request.query_params.get("resume_id")
        if raw is not None:
            if not raw.strip().isdigit():
                raise ValidationError({"resume_id": ["Send the id of one of your resumes."]})
            resume = resumes.filter(pk=int(raw)).first()
            if resume is None:
                raise NotFound("Resume not found.")  # someone else's resume gives 404 too
            if resume.parsing_status != Resume.ParsingStatus.SUCCESS:
                raise ValidationError({"resume_id": ["This resume could not be parsed, so it cannot be analysed."]})
            return resume
        resume = resumes.filter(is_active=True, parsing_status=Resume.ParsingStatus.SUCCESS).first()
        if resume is None:
            raise ValidationError({"resume": ["Upload a resume to analyse your skills."]})
        return resume


class JobSkillGapAISummaryView(JobSkillGapView):
    """POST /api/skill-gap/jobs/<job_id>/ai-summary/   (candidate)

    The same analysis as GET /api/skill-gap/jobs/<job_id>/, plus a short natural-language summary
    written by the LLM. The matched/partial/missing lists still come from analysis.analyze(); the
    LLM only puts them into words, and is checked so it cannot add skills of its own.
    POST because every call makes a Gemini request (and is rate limited).
    """

    http_method_names = ["post", "options"]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"

    def post(self, request, job_id):
        job, resume, result = self.analyse(request, job_id)
        try:
            summary, llm_result = ai_summary.summarise(job.job_title, result)
        except LLMError as error:
            raise AIUnavailable(error)
        return Response(
            {
                **self.header(job, resume),
                "coverage_percent": result["coverage_percent"],
                "matched": [row["skill"] for row in result["matched"]],
                "partial": [row["skill"] for row in result["partial"]],
                "missing": [row["skill"] for row in result["missing"]],
                "ai_summary": summary,
                "model_name": llm_result.model,
                "note": ai_summary.NOTE,
            }
        )