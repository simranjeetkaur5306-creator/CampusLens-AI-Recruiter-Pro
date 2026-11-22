"""Email notifications (Phase 16).

Rules this module follows:
* It NEVER raises. A failed email must not break the action that triggered it (applying,
  changing a status, scheduling an interview). Every function returns a status string instead.
* It NEVER pretends. The returned status is exactly what happened:
    "sent"            the mail server accepted the message
    "not_configured"  SMTP settings are missing, nothing was sent
    "failed"          the server refused or could not be reached
    "console"         development mode: the message was printed/saved locally, not delivered
    "skipped"         there was nobody to send to
* Emails contain no resume text and no contact details of the other party.
"""
import logging
from functools import wraps

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)

SENT = "sent"
NOT_CONFIGURED = "not_configured"
FAILED = "failed"
CONSOLE = "console"
SKIPPED = "skipped"

FOOTER = (
    "\n\n--\nCampusLens AI\n"
    "This is an automated message. Hiring decisions are made by people, not by this system."
)


def delivery_mode():
    """How emails leave the server right now: "deliver", "console" or "not_configured"."""
    backend = settings.EMAIL_BACKEND
    if backend.endswith("smtp.EmailBackend"):
        return "deliver" if settings.EMAIL_HOST else "not_configured"
    if backend.endswith(("console.EmailBackend", "filebased.EmailBackend")):
        return "console"
    if backend.endswith("dummy.EmailBackend"):
        return "not_configured"
    return "deliver"  # locmem (used by tests) or a custom backend


def send_email(to, subject, body):
    """Send one plain-text email. Returns one of the status strings above; never raises."""
    if not to:
        return SKIPPED
    mode = delivery_mode()
    if mode == "not_configured":
        return NOT_CONFIGURED
    subject = " ".join(str(subject).split())[:200]  # one line only: protects against header injection
    try:
        sent = send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False)
    except Exception:
        # The recipient and the body are deliberately not logged (personal data).
        logger.exception("Could not send email with subject %r", subject)
        return FAILED
    if not sent:
        return FAILED
    return CONSOLE if mode == "console" else SENT


def safe(function):
    """Turns any unexpected error (for example missing related data) into "failed"."""

    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception:
            logger.exception("Notification %s crashed", function.__name__)
            return FAILED

    return wrapper


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _name(user):
    return f"{user.first_name} {user.last_name}".strip() or user.email


def _link(path):
    return f"{settings.FRONTEND_URL}{path}"


def _company(job):
    return job.company_name or "the company"


def _when(moment):
    local = timezone.localtime(moment)
    return f"{local:%A, %d %B %Y, %I:%M %p} ({local.tzname()})"


WHERE_LABEL = {"online": "Meeting link", "in_person": "Address", "phone": "Phone / instructions"}


def _interview_block(interview):
    lines = [
        f"When:      {_when(interview.scheduled_at)}",
        f"Duration:  {interview.duration_minutes} minutes",
        f"Mode:      {interview.get_mode_display()}",
    ]
    if interview.location:
        lines.append(f"{WHERE_LABEL.get(interview.mode, 'Where')}: {interview.location}")
    if interview.details:
        lines.append(f"Details:   {interview.details}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# candidate emails
# ---------------------------------------------------------------------------
@safe
def application_received(application):
    user, job = application.candidate.user, application.job
    body = (
        f"Hello {_name(user)},\n\n"
        f"We received your application for {job.job_title} at {_company(job)}.\n"
        "A recruiter will review it. You will get an email if its status changes.\n\n"
        f"Track your applications: {_link('/candidate/applications')}"
        + FOOTER
    )
    return send_email(user.email, f"Application received: {job.job_title}", body)


@safe
def application_shortlisted(application):
    user, job = application.candidate.user, application.job
    body = (
        f"Hello {_name(user)},\n\n"
        f"Your application for {job.job_title} at {_company(job)} has been shortlisted.\n"
        "This is not a job offer. The recruiter will contact you about the next steps.\n\n"
        f"See your applications: {_link('/candidate/applications')}"
        + FOOTER
    )
    return send_email(user.email, f"You were shortlisted: {job.job_title}", body)


@safe
def application_rejected(application, interviews_cancelled=0):
    user, job = application.candidate.user, application.job
    extra = "\nAny interview that was scheduled for this application has been cancelled.\n" if interviews_cancelled else ""
    body = (
        f"Hello {_name(user)},\n\n"
        f"Thank you for applying for {job.job_title} at {_company(job)}. "
        "After reviewing your application, the recruiter has decided not to move forward with it.\n"
        f"{extra}\n"
        "This is not a judgement of your potential. You can compare your skills with other roles here:\n"
        f"{_link('/candidate/recommendations')}"
        + FOOTER
    )
    return send_email(user.email, f"Update on your application: {job.job_title}", body)


@safe
def interview_scheduled(interview):
    application = interview.application
    user, job = application.candidate.user, application.job
    body = (
        f"Hello {_name(user)},\n\n"
        f"An interview has been scheduled for your application to {job.job_title} at {_company(job)}.\n\n"
        f"{_interview_block(interview)}\n\n"
        "Please be ready a few minutes early. If you cannot attend, contact the recruiter as soon as possible.\n\n"
        f"Your applications: {_link('/candidate/applications')}"
        + FOOTER
    )
    return send_email(user.email, f"Interview scheduled: {job.job_title}", body)


@safe
def interview_updated(interview):
    application = interview.application
    user, job = application.candidate.user, application.job
    body = (
        f"Hello {_name(user)},\n\n"
        f"The details of your interview for {job.job_title} at {_company(job)} have changed. "
        "Please use the new details below.\n\n"
        f"{_interview_block(interview)}\n\n"
        f"Your applications: {_link('/candidate/applications')}"
        + FOOTER
    )
    return send_email(user.email, f"Interview updated: {job.job_title}", body)


@safe
def interview_cancelled(interview):
    application = interview.application
    user, job = application.candidate.user, application.job
    body = (
        f"Hello {_name(user)},\n\n"
        f"Your interview for {job.job_title} at {_company(job)}, planned for "
        f"{_when(interview.scheduled_at)}, has been cancelled.\n"
        "The recruiter may contact you to arrange a new time."
        + FOOTER
    )
    return send_email(user.email, f"Interview cancelled: {job.job_title}", body)


# ---------------------------------------------------------------------------
# recruiter emails
# ---------------------------------------------------------------------------
@safe
def new_application_for_recruiter(application):
    job = application.job
    recruiter_user = job.recruiter.user
    body = (
        f"Hello {_name(recruiter_user)},\n\n"
        f"{_name(application.candidate.user)} applied for {job.job_title}.\n\n"
        f"Review the application: {_link(f'/recruiter/applicants/{application.pk}')}"
        + FOOTER
    )
    return send_email(recruiter_user.email, f"New application: {job.job_title}", body)