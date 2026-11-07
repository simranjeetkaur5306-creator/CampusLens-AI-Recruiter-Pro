from django.conf import settings
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCandidate
from candidates.models import Candidate

from .exceptions import ResumeFileError
from .models import Resume
from .serializers import ResumeDetailSerializer, ResumeListSerializer, ResumeUploadSerializer
from .services import resume_service

CANDIDATE_ONLY = [IsAuthenticated, IsCandidate]


def get_candidate(user):
    candidate, _ = Candidate.objects.get_or_create(user=user)
    return candidate


def own_resumes(user):
    """Only the logged-in candidate's resumes: this is the ownership check."""
    return (
        Resume.objects.filter(candidate__user=user)
        .select_related("candidate__user")
        .prefetch_related("skills")
    )


class ResumeUploadView(APIView):
    permission_classes = CANDIDATE_ONLY
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Reject absurdly large requests before reading the body
        try:
            declared = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            declared = 0
        if declared > settings.RESUME_MAX_SIZE_BYTES + 1024 * 1024:
            raise ValidationError({"file": ["File is too large. Maximum allowed size is 5 MB."]})

        serializer = ResumeUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            resume = resume_service.upload_resume(
                get_candidate(request.user), serializer.validated_data["file"]
            )
        except ResumeFileError as exc:
            raise ValidationError({"file": [str(exc)]})

        if resume.parsing_status == Resume.ParsingStatus.SUCCESS:
            message = "Resume uploaded and parsed successfully."
        else:
            message = "Resume uploaded, but its text could not be parsed. See parsing_error."
        return Response(
            {"message": message, "resume": ResumeDetailSerializer(resume).data},
            status=status.HTTP_201_CREATED,
        )


class ResumeListView(generics.ListAPIView):
    """All of the logged-in candidate's resume versions (newest first)."""

    serializer_class = ResumeListSerializer
    permission_classes = CANDIDATE_ONLY

    def get_queryset(self):
        return own_resumes(self.request.user)


class ActiveResumeView(APIView):
    """The candidate's current (active) resume with all parsed details."""

    permission_classes = CANDIDATE_ONLY

    def get(self, request):
        resume = own_resumes(request.user).filter(is_active=True).first()
        if resume is None:
            raise NotFound("No active resume found. Upload a resume first.")
        return Response(ResumeDetailSerializer(resume).data)


class ResumeDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = CANDIDATE_ONLY
    serializer_class = ResumeDetailSerializer

    def get_queryset(self):
        # someone else's resume id gives 404 (not 403), so its existence is not revealed
        return own_resumes(self.request.user)

    def perform_destroy(self, instance):
        resume_service.delete_resume(instance)

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response({"message": "Resume deleted."}, status=status.HTTP_200_OK)


class ResumeActivateView(APIView):
    """Makes one of the candidate's successfully parsed resumes the active one."""

    permission_classes = CANDIDATE_ONLY

    def post(self, request, pk):
        resume = generics.get_object_or_404(own_resumes(request.user), pk=pk)
        if resume.parsing_status != Resume.ParsingStatus.SUCCESS:
            raise ValidationError({"resume": ["Only successfully parsed resumes can be made active."]})
        resume_service.make_active(resume)
        return Response({"message": "Resume set as active.", "resume": ResumeListSerializer(resume).data})