from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsRecruiter
from recruiters.models import Recruiter

from .services import DEFAULT_DAYS, MAX_DAYS, MIN_DAYS, recruiter_overview


def parse_days(raw):
    if raw is None:
        return DEFAULT_DAYS
    text = str(raw).strip()
    if not text.isdigit() or not MIN_DAYS <= int(text) <= MAX_DAYS:
        raise ValidationError({"days": [f"Use a whole number from {MIN_DAYS} to {MAX_DAYS}."]})
    return int(text)


class RecruiterOverviewView(APIView):
    """GET /api/analytics/recruiter/overview/?days=30   (recruiter only)

    Statistics about the logged-in recruiter's own jobs and applicants, calculated from the
    database on every request. `days` (7-90) sets the length of the applications-over-time chart.
    """

    permission_classes = [IsAuthenticated, IsRecruiter]

    def get(self, request):
        days = parse_days(request.query_params.get("days"))
        recruiter, _ = Recruiter.objects.get_or_create(user=request.user)
        return Response(recruiter_overview(recruiter, days))