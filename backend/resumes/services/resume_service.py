import logging
import os
import re

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..exceptions import ResumeFileError, ResumeParseError
from ..models import Resume, Skill
from ..validators import validate_resume_file
from .parser import parse_resume

logger = logging.getLogger(__name__)


def _safe_filename(name):
    base = os.path.basename((name or "").replace("\\", "/"))
    base = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()
    return base[:255] or "resume"


def upload_resume(candidate, uploaded_file):
    """Validates, stores and parses an uploaded resume. Returns the saved Resume.

    - Invalid files raise ResumeFileError and nothing is saved.
    - A valid file that has no readable text is saved with parsing_status="failed"
      (and is not made active), so the candidate can see why and delete it.
    - A successfully parsed resume becomes the candidate's active resume.
    """
    file_type, data = validate_resume_file(uploaded_file)

    if Resume.objects.filter(candidate=candidate).count() >= settings.RESUME_MAX_PER_CANDIDATE:
        raise ResumeFileError(
            f"You can keep up to {settings.RESUME_MAX_PER_CANDIDATE} resumes. "
            "Delete an old one before uploading a new one."
        )

    parsed, error = None, ""
    try:
        parsed = parse_resume(data, file_type)
    except ResumeParseError as exc:
        error = str(exc)

    resume = Resume(
        candidate=candidate,
        file=uploaded_file,
        original_filename=_safe_filename(uploaded_file.name),
        file_type=file_type,
        file_size=len(data),
        parsed_at=timezone.now(),
    )
    if parsed:
        resume.parsing_status = Resume.ParsingStatus.SUCCESS
        resume.extracted_text = parsed["text"]
        resume.contact = parsed["contact"]
        resume.education = parsed["education"]
        resume.experience = parsed["experience"]
        resume.projects = parsed["projects"]
        resume.certifications = parsed["certifications"]
    else:
        resume.parsing_status = Resume.ParsingStatus.FAILED
        resume.parsing_error = error

    try:
        with transaction.atomic():
            resume.save()  # this also writes the file to storage
            if parsed:
                skills = [
                    Skill.objects.get_or_create(name=item["name"], defaults={"category": item["category"]})[0]
                    for item in parsed["skills"]
                ]
                resume.skills.set(skills)
                make_active(resume)
    except Exception:
        # do not leave an orphan file behind if the database work failed
        name = resume.file.name or ""
        if name.startswith("resumes/"):
            resume.file.storage.delete(name)
        raise
    return resume


def make_active(resume):
    """Makes this resume the candidate's only active one."""
    Resume.objects.filter(candidate=resume.candidate, is_active=True).exclude(pk=resume.pk).update(is_active=False)
    if not resume.is_active:
        resume.is_active = True
        resume.save(update_fields=["is_active"])


def delete_resume(resume):
    """Deletes a resume (the file is removed by the post_delete signal).

    If it was the active one, the newest successfully parsed resume becomes active.
    """
    candidate, was_active = resume.candidate, resume.is_active
    with transaction.atomic():
        resume.delete()
        if was_active:
            replacement = (
                Resume.objects.filter(candidate=candidate, parsing_status=Resume.ParsingStatus.SUCCESS)
                .order_by("-uploaded_at")
                .first()
            )
            if replacement:
                make_active(replacement)