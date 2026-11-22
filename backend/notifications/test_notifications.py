from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from applications.models import Application
from candidates.models import Candidate
from matching.factories import LoginMixin, make_candidate, make_job, make_recruiter, make_resume
from recruiters.models import Recruiter

from . import services

SMTP = "django.core.mail.backends.smtp.EmailBackend"


class SendEmailTests(TestCase):
    def test_sends_through_the_configured_backend(self):
        self.assertEqual(services.send_email("a@example.com", "Hello", "Body"), services.SENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["a@example.com"])

    def test_nobody_to_send_to_is_skipped(self):
        self.assertEqual(services.send_email("", "Hello", "Body"), services.SKIPPED)
        self.assertEqual(mail.outbox, [])

    @override_settings(EMAIL_BACKEND=SMTP, EMAIL_HOST="")
    def test_missing_smtp_settings_are_reported_not_hidden(self):
        self.assertEqual(services.delivery_mode(), "not_configured")
        self.assertEqual(services.send_email("a@example.com", "Hello", "Body"), services.NOT_CONFIGURED)
        self.assertEqual(mail.outbox, [])

    @override_settings(EMAIL_BACKEND=SMTP, EMAIL_HOST="smtp.example.com")
    def test_a_failing_server_gives_failed_and_never_raises(self):
        with patch("notifications.services.send_mail", side_effect=OSError("connection refused")):
            self.assertEqual(services.send_email("a@example.com", "Hello", "Body"), services.FAILED)

    def test_nothing_sent_counts_as_failed(self):
        with patch("notifications.services.send_mail", return_value=0):
            self.assertEqual(services.send_email("a@example.com", "Hello", "Body"), services.FAILED)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_console_backend_is_not_called_sent(self):
        with patch("notifications.services.send_mail", return_value=1):
            self.assertEqual(services.send_email("a@example.com", "Hello", "Body"), services.CONSOLE)

    def test_subject_is_one_line(self):
        services.send_email("a@example.com", "Line one\r\nBcc: evil@example.com", "Body")
        self.assertNotIn("\n", mail.outbox[0].subject)
        self.assertNotIn("\r", mail.outbox[0].subject)

    def test_unexpected_errors_become_failed(self):
        @services.safe
        def broken():
            raise RuntimeError("boom")

        self.assertEqual(broken(), services.FAILED)


class EventEmailTests(TestCase):
    def setUp(self):
        self.recruiter = make_recruiter("hr@example.com")
        self.job = make_job(self.recruiter, title="Backend Developer")
        self.candidate = make_candidate("asha@example.com")
        self.application = Application.objects.create(
            candidate=self.candidate, job=self.job, resume=make_resume(self.candidate)
        )

    def test_candidate_gets_a_confirmation_without_any_resume_data(self):
        self.assertEqual(services.application_received(self.application), services.SENT)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["asha@example.com"])
        self.assertIn("Application received: Backend Developer", message.subject)
        self.assertIn("/candidate/applications", message.body)
        self.assertNotIn("extracted", message.body.lower())

    def test_recruiter_is_told_about_a_new_application_without_the_candidates_email(self):
        self.assertEqual(services.new_application_for_recruiter(self.application), services.SENT)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["hr@example.com"])
        self.assertIn(f"/recruiter/applicants/{self.application.pk}", message.body)
        self.assertNotIn("asha@example.com", message.body)

    def test_shortlisted_and_rejected_emails(self):
        self.assertEqual(services.application_shortlisted(self.application), services.SENT)
        self.assertEqual(services.application_rejected(self.application, interviews_cancelled=1), services.SENT)
        self.assertIn("shortlisted", mail.outbox[0].subject.lower())
        self.assertIn("not a job offer", mail.outbox[0].body)
        self.assertIn("cancelled", mail.outbox[1].body)
        self.assertEqual({m.to[0] for m in mail.outbox}, {"asha@example.com"})


class ApplyEmailTests(LoginMixin, APITestCase):
    def test_applying_sends_two_emails_and_reports_the_candidates_one(self):
        recruiter = make_recruiter("hr@example.com")
        job = make_job(recruiter, title="Backend Developer")
        user = self.login_as("candidate", "asha@example.com")
        make_resume(Candidate.objects.get(user=user))
        res = self.client.post("/api/applications/", {"job": job.pk}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["email"], {"status": "sent", "recipient": "you"})
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["asha@example.com", "hr@example.com"])

    @override_settings(EMAIL_BACKEND=SMTP, EMAIL_HOST="")
    def test_applying_still_works_when_email_is_not_configured(self):
        recruiter = make_recruiter("hr@example.com")
        job = make_job(recruiter)
        user = self.login_as("candidate", "asha@example.com")
        make_resume(Candidate.objects.get(user=user))
        res = self.client.post("/api/applications/", {"job": job.pk}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["email"]["status"], "not_configured")
        self.assertEqual(Application.objects.count(), 1)


class StatusEmailTests(LoginMixin, APITestCase):
    def setUp(self):
        owner = self.login_as("recruiter", "owner@example.com")
        self.job = make_job(Recruiter.objects.get(user=owner), title="Backend Developer")
        candidate = make_candidate("asha@example.com")
        self.application = Application.objects.create(candidate=candidate, job=self.job, resume=make_resume(candidate))
        self.url = f"/api/applications/{self.application.pk}/status/"
        mail.outbox.clear()

    def test_shortlisting_emails_the_candidate_and_says_so(self):
        res = self.client.patch(self.url, {"status": "shortlisted"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["email"], {"status": "sent", "recipient": "candidate"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["asha@example.com"])

    def test_rejecting_emails_the_candidate(self):
        res = self.client.patch(self.url, {"status": "rejected"}, format="json")
        self.assertEqual(res.data["email"]["status"], "sent")
        self.assertIn("Update on your application", mail.outbox[0].subject)

    def test_resetting_to_applied_sends_no_email(self):
        self.client.patch(self.url, {"status": "shortlisted"}, format="json")
        mail.outbox.clear()
        res = self.client.patch(self.url, {"status": "applied"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("email", res.data)
        self.assertEqual(mail.outbox, [])

    def test_repeating_the_same_status_does_not_email_again(self):
        self.client.patch(self.url, {"status": "shortlisted"}, format="json")
        mail.outbox.clear()
        self.client.patch(self.url, {"status": "shortlisted"}, format="json")
        self.assertEqual(mail.outbox, [])

    @override_settings(EMAIL_BACKEND=SMTP, EMAIL_HOST="smtp.example.com")
    def test_a_mail_server_failure_does_not_undo_the_status_change(self):
        with patch("notifications.services.send_mail", side_effect=OSError("down")):
            res = self.client.patch(self.url, {"status": "shortlisted"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["email"]["status"], "failed")
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "shortlisted")