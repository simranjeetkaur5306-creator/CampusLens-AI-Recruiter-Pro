from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from applications.models import Application
from matching.factories import LoginMixin, make_candidate, make_job, make_recruiter, make_resume
from recruiters.models import Recruiter

from .models import Interview

OWNER = "owner@example.com"
SMTP = "django.core.mail.backends.smtp.EmailBackend"


def when(days=2, hour=10):
    moment = timezone.localtime(timezone.now() + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
    return moment.isoformat()


def payload(**overrides):
    body = {
        "scheduled_at": when(),
        "duration_minutes": 45,
        "mode": "online",
        "location": "https://meet.example.com/abc-defg",
        "details": "Bring your laptop.",
    }
    body.update(overrides)
    return body


class Base(LoginMixin, APITestCase):
    """The owner has one job with an applicant; another recruiter has a job with an applicant."""

    def setUp(self):
        owner_user = self.login_as("recruiter", OWNER)
        self.owner = Recruiter.objects.get(user=owner_user)
        self.job = make_job(self.owner, title="Backend Developer")
        self.application = self.apply("asha@example.com", self.job)
        self.foreign = self.apply("ravi@example.com", make_job(make_recruiter("other@example.com"), title="Foreign"))
        self.schedule_url = f"/api/interviews/applications/{self.application.pk}/schedule/"
        mail.outbox.clear()

    def apply(self, email, job):
        candidate = make_candidate(email)
        return Application.objects.create(candidate=candidate, job=job, resume=make_resume(candidate))

    def as_owner(self):
        self.client.credentials()
        self.login_as("recruiter", OWNER)

    def schedule(self, **overrides):
        return self.client.post(self.schedule_url, payload(**overrides), format="json")


class CreateTests(Base):
    def test_scheduling_creates_the_interview_updates_the_status_and_emails_the_candidate(self):
        res = self.schedule()
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["status"], "scheduled")
        self.assertEqual(res.data["mode"], "online")
        self.assertEqual(res.data["application"]["candidate"]["email"], "asha@example.com")
        self.assertEqual(res.data["email"], {"status": "sent", "recipient": "candidate"})

        interview = Interview.objects.get()
        self.assertEqual(interview.application_id, self.application.pk)
        self.assertEqual(interview.duration_minutes, 45)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "interview_scheduled")

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["asha@example.com"])
        self.assertIn("Interview scheduled: Backend Developer", message.subject)
        self.assertIn("https://meet.example.com/abc-defg", message.body)
        self.assertIn("Bring your laptop.", message.body)
        self.assertIn("45 minutes", message.body)

    def test_the_counts_in_analytics_follow(self):
        self.schedule()
        totals = self.client.get("/api/analytics/recruiter/overview/").data["totals"]
        self.assertEqual(totals["interviews_scheduled"], 1)

    def test_candidate_sees_the_interview_on_the_application(self):
        self.schedule()
        self.client.credentials()
        self.client.force_authenticate(user=self.application.candidate.user)
        row = self.client.get("/api/applications/me/").data["results"][0]
        self.assertEqual(row["status"], "interview_scheduled")
        self.assertEqual(row["next_interview"]["mode"], "online")
        self.assertEqual(row["next_interview"]["location"], "https://meet.example.com/abc-defg")
        self.assertEqual(row["next_interview"]["duration_minutes"], 45)

    def test_a_cancelled_interview_is_not_shown_to_the_candidate(self):
        interview_id = self.schedule().data["id"]
        self.client.patch(f"/api/interviews/schedule/{interview_id}/", {"status": "cancelled"}, format="json")
        self.client.credentials()
        self.client.force_authenticate(user=self.application.candidate.user)
        row = self.client.get("/api/applications/me/").data["results"][0]
        self.assertIsNone(row["next_interview"])

    def test_validation(self):
        bad = [
            payload(scheduled_at=when(days=-1)),                         # in the past
            payload(scheduled_at=when(days=400)),                        # more than a year ahead
            payload(duration_minutes=4),
            payload(duration_minutes=481),
            payload(mode="online", location=""),                        # online needs a link
            payload(mode="online", location="not a link"),
            payload(mode="online", location="javascript:alert(1)"),     # only http(s) links
            payload(mode="in_person", location="  "),                   # in person needs an address
            payload(mode="video"),                                      # unknown mode
            {**payload(), "status": "completed"},                       # server decides the status
            {**payload(), "application": 1},                            # and the application
        ]
        for body in bad:
            res = self.client.post(self.schedule_url, body, format="json")
            self.assertEqual(res.status_code, 400, body)
        self.assertEqual(Interview.objects.count(), 0)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "applied")
        self.assertEqual(mail.outbox, [])

    def test_phone_interview_does_not_need_a_location(self):
        self.assertEqual(self.schedule(mode="phone", location="").status_code, 201)

    def test_only_one_scheduled_interview_per_application(self):
        self.assertEqual(self.schedule().status_code, 201)
        res = self.schedule(scheduled_at=when(days=3))
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Interview.objects.count(), 1)

    def test_a_rejected_application_cannot_be_scheduled(self):
        Application.objects.filter(pk=self.application.pk).update(status="rejected")
        self.assertEqual(self.schedule().status_code, 400)

    def test_another_recruiters_application_is_404(self):
        res = self.client.post(f"/api/interviews/applications/{self.foreign.pk}/schedule/", payload(), format="json")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(Interview.objects.count(), 0)

    def test_candidates_and_anonymous_users_are_refused(self):
        self.client.credentials()
        self.assertEqual(self.client.post(self.schedule_url, payload(), format="json").status_code, 401)
        self.login_as("candidate", "someone@example.com")
        self.assertEqual(self.client.post(self.schedule_url, payload(), format="json").status_code, 403)

    @override_settings(EMAIL_BACKEND=SMTP, EMAIL_HOST="")
    def test_scheduling_works_without_smtp_and_says_the_email_was_not_sent(self):
        res = self.schedule()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["email"]["status"], "not_configured")
        self.assertEqual(Interview.objects.count(), 1)

    @override_settings(EMAIL_BACKEND=SMTP, EMAIL_HOST="smtp.example.com")
    def test_scheduling_survives_a_mail_server_failure(self):
        with patch("notifications.services.send_mail", side_effect=OSError("down")):
            res = self.schedule()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["email"]["status"], "failed")
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "interview_scheduled")


class UpdateTests(Base):
    def setUp(self):
        super().setUp()
        self.interview_id = self.schedule().data["id"]
        self.url = f"/api/interviews/schedule/{self.interview_id}/"
        mail.outbox.clear()

    def patch(self, body, url=None):
        return self.client.patch(url or self.url, body, format="json")

    def test_changing_the_time_updates_and_emails_the_candidate(self):
        res = self.patch({"scheduled_at": when(days=4, hour=15), "location": "https://meet.example.com/new"})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["email"], {"status": "sent", "recipient": "candidate"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Interview updated", mail.outbox[0].subject)
        self.assertIn("https://meet.example.com/new", mail.outbox[0].body)
        self.assertEqual(Interview.objects.get().location, "https://meet.example.com/new")

    def test_sending_the_same_values_changes_nothing_and_sends_no_email(self):
        res = self.patch({"mode": "online", "duration_minutes": 45})
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("email", res.data)
        self.assertEqual(mail.outbox, [])

    def test_validation_on_edit(self):
        for body in (
            {},
            {"scheduled_at": when(days=-2)},
            {"mode": "in_person", "location": ""},        # in-person needs an address
            {"mode": "phone", "bogus": 1},
            {"duration_minutes": 2},
        ):
            self.assertEqual(self.patch(body).status_code, 400, body)
        self.assertEqual(mail.outbox, [])

    def test_cancelling_puts_the_application_back_to_shortlisted_and_emails(self):
        res = self.patch({"status": "cancelled"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "cancelled")
        self.assertEqual(res.data["email"]["status"], "sent")
        self.assertIn("Interview cancelled", mail.outbox[0].subject)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "shortlisted")
        # a new interview can now be scheduled
        self.assertEqual(self.schedule(scheduled_at=when(days=5)).status_code, 201)

    def test_completed_needs_the_start_time_to_have_passed(self):
        self.assertEqual(self.patch({"status": "completed"}).status_code, 400)
        Interview.objects.filter(pk=self.interview_id).update(scheduled_at=timezone.now() - timedelta(hours=2))
        res = self.patch({"status": "completed"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "completed")
        self.assertEqual(mail.outbox, [])  # no email for a plain completion
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "interview_scheduled")

    def test_a_finished_interview_cannot_be_edited(self):
        self.patch({"status": "cancelled"})
        self.assertEqual(self.patch({"details": "late change"}).status_code, 400)

    def test_another_recruiter_gets_404(self):
        other = Interview.objects.create(
            application=self.foreign, scheduled_at=timezone.now() + timedelta(days=3), mode="phone"
        )
        self.assertEqual(self.patch({"details": "x"}, url=f"/api/interviews/schedule/{other.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/interviews/schedule/{other.pk}/").status_code, 404)
        other.refresh_from_db()
        self.assertEqual(other.details, "")


class StatusRulesTests(Base):
    def setUp(self):
        super().setUp()
        self.schedule()
        self.status_url = f"/api/applications/{self.application.pk}/status/"
        mail.outbox.clear()

    def test_cannot_shortlist_while_an_interview_is_scheduled(self):
        res = self.client.patch(self.status_url, {"status": "shortlisted"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Interview.objects.get().status, "scheduled")
        self.assertEqual(mail.outbox, [])

    def test_rejecting_cancels_the_interview_and_tells_the_candidate(self):
        res = self.client.patch(self.status_url, {"status": "rejected"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Interview.objects.get().status, "cancelled")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("cancelled", mail.outbox[0].body)

    def test_after_cancelling_the_recruiter_can_shortlist_again(self):
        interview_id = Interview.objects.get().pk
        self.client.patch(f"/api/interviews/schedule/{interview_id}/", {"status": "cancelled"}, format="json")
        res = self.client.patch(self.status_url, {"status": "applied"}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_interview_scheduled_still_cannot_be_chosen_by_hand(self):
        res = self.client.patch(self.status_url, {"status": "interview_scheduled"}, format="json")
        self.assertEqual(res.status_code, 400)


class ListTests(Base):
    def test_lists_only_own_interviews_with_filters(self):
        self.schedule()
        Interview.objects.create(application=self.foreign, scheduled_at=timezone.now() + timedelta(days=3), mode="phone")
        Interview.objects.create(
            application=self.application, scheduled_at=timezone.now() - timedelta(days=1), mode="phone", status="completed"
        )
        rows = self.client.get("/api/interviews/schedule/").data["results"]
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["application"]["id"] for r in rows}, {self.application.pk})
        scheduled = self.client.get("/api/interviews/schedule/", {"status": "scheduled"}).data["results"]
        self.assertEqual([r["status"] for r in scheduled], ["scheduled"])
        by_app = self.client.get("/api/interviews/schedule/", {"application": self.application.pk}).data["results"]
        self.assertEqual(len(by_app), 2)

    def test_bad_filters_and_roles(self):
        self.assertEqual(self.client.get("/api/interviews/schedule/", {"status": "nope"}).status_code, 400)
        self.assertEqual(self.client.get("/api/interviews/schedule/", {"application": "x"}).status_code, 400)
        self.login_as("candidate", "someone@example.com")
        self.assertEqual(self.client.get("/api/interviews/schedule/").status_code, 403)