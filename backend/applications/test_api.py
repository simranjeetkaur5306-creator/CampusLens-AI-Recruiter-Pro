from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from candidates.models import Candidate
from jobs.models import Job
from matching.factories import LoginMixin, make_job, make_recruiter, make_resume
from resumes.models import Resume

from .models import Application

APPLY = "/api/applications/"
MINE = "/api/applications/me/"


class ApplyTests(LoginMixin, APITestCase):
    def setUp(self):
        self.recruiter = make_recruiter()
        self.job = make_job(self.recruiter, title="Backend Developer")

    def candidate_with_resume(self, email="cand@example.com", **resume_kwargs):
        user = self.login_as("candidate", email)
        candidate = Candidate.objects.get(user=user)
        return candidate, make_resume(candidate, **resume_kwargs)

    def apply(self, job_id=None, **extra):
        return self.client.post(APPLY, {"job": job_id or self.job.pk, **extra}, format="json")

    def test_candidate_applies_with_the_active_resume(self):
        candidate, resume = self.candidate_with_resume()
        res = self.apply()
        self.assertEqual(res.status_code, 201)
        application = res.data["application"]
        self.assertEqual(application["status"], "applied")
        self.assertEqual(application["job"]["job_title"], "Backend Developer")
        self.assertEqual(application["resume"]["id"], resume.pk)
        row = Application.objects.get(pk=application["id"])
        self.assertEqual((row.candidate, row.job, row.resume), (candidate, self.job, resume))

    def test_application_keeps_the_resume_that_was_active_when_applying(self):
        candidate, first = self.candidate_with_resume()
        other_job = make_job(self.recruiter, title="Data Analyst")
        first_application = self.apply().data["application"]["id"]
        Resume.objects.filter(pk=first.pk).update(is_active=False)
        second = make_resume(candidate, text="A newer resume about data analysis with SQL and Tableau.")
        second_application = self.apply(other_job.pk).data["application"]["id"]
        self.assertEqual(Application.objects.get(pk=first_application).resume, first)
        self.assertEqual(Application.objects.get(pk=second_application).resume, second)

    def test_cannot_apply_twice_to_the_same_job(self):
        self.candidate_with_resume()
        self.assertEqual(self.apply().status_code, 201)
        res = self.apply()
        self.assertEqual(res.status_code, 400)
        self.assertIn("already applied", res.data["errors"]["job"][0])
        self.assertEqual(Application.objects.count(), 1)

    def test_can_apply_to_different_jobs(self):
        self.candidate_with_resume()
        other = make_job(self.recruiter, title="Data Analyst")
        self.assertEqual(self.apply().status_code, 201)
        self.assertEqual(self.apply(other.pk).status_code, 201)

    def test_an_active_parsed_resume_is_required(self):
        user = self.login_as("candidate", "noresume@example.com")
        res = self.apply()
        self.assertEqual(res.status_code, 400)
        self.assertIn("resume", res.data["errors"])
        candidate = Candidate.objects.get(user=user)
        make_resume(candidate, active=False)               # exists, but not the active one
        self.assertEqual(self.apply().status_code, 400)
        make_resume(candidate, status="failed", active=True)  # active, but its text could not be parsed
        self.assertEqual(self.apply().status_code, 400)
        self.assertEqual(Application.objects.count(), 0)

    def test_job_must_exist_and_be_open(self):
        self.candidate_with_resume()
        closed = make_job(self.recruiter, title="Closed role", active=False)
        for payload in ({"job": closed.pk}, {"job": 999999}, {"job": "abc"}, {"job": None}, {}):
            res = self.client.post(APPLY, payload, format="json")
            self.assertEqual(res.status_code, 400, payload)
            self.assertIn("job", res.data["errors"], payload)
        self.assertEqual(Application.objects.count(), 0)

    def test_client_cannot_choose_status_candidate_or_resume(self):
        _candidate, resume = self.candidate_with_resume()
        for extra in ({"status": "shortlisted"}, {"candidate": 1}, {"resume": resume.pk}, {"applied_at": "2020-01-01"}):
            res = self.apply(**extra)
            self.assertEqual(res.status_code, 400, extra)
            self.assertIn(next(iter(extra)), res.data["errors"])
        self.assertEqual(Application.objects.count(), 0)

    def test_only_candidates_can_apply(self):
        self.login_as("recruiter", "other-recruiter@example.com")
        self.assertEqual(self.apply().status_code, 403)
        self.client.credentials()
        self.assertEqual(self.apply().status_code, 401)
        self.assertEqual(Application.objects.count(), 0)

    def test_the_database_itself_rejects_duplicates(self):
        candidate, resume = self.candidate_with_resume()
        Application.objects.create(candidate=candidate, job=self.job, resume=resume)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Application.objects.create(candidate=candidate, job=self.job, resume=resume)


class MyApplicationsTests(LoginMixin, APITestCase):
    def setUp(self):
        recruiter = make_recruiter()
        self.job1 = make_job(recruiter, title="First Job")
        self.job2 = make_job(recruiter, title="Second Job")

    def candidate(self, email):
        user = self.login_as("candidate", email)
        candidate = Candidate.objects.get(user=user)
        make_resume(candidate)
        return candidate

    def test_lists_only_my_applications_newest_first(self):
        self.candidate("a@example.com")
        self.client.post(APPLY, {"job": self.job1.pk}, format="json")
        self.client.post(APPLY, {"job": self.job2.pk}, format="json")
        self.candidate("b@example.com")
        self.client.post(APPLY, {"job": self.job1.pk}, format="json")
        self.login_as("candidate", "a@example.com")
        res = self.client.get(MINE)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 2)
        self.assertEqual([row["job"]["job_title"] for row in res.data["results"]], ["Second Job", "First Job"])
        row = res.data["results"][0]
        self.assertEqual(row["status"], "applied")
        self.assertEqual(row["resume"]["original_filename"], "x.pdf")
        self.assertEqual(set(row["job"]), {"id", "job_title", "company_name", "location", "job_type", "is_active"})

    def test_no_private_data_in_the_response(self):
        self.candidate("a@example.com")
        self.client.post(APPLY, {"job": self.job1.pk}, format="json")
        text = str(self.client.get(MINE).data)
        for forbidden in ("embedding", "extracted_text", "description"):
            self.assertNotIn(forbidden, text)

    def test_empty_list(self):
        self.login_as("candidate", "new@example.com")
        res = self.client.get(MINE)
        self.assertEqual((res.status_code, res.data["count"]), (200, 0))

    def test_only_candidates_can_list(self):
        self.client.credentials()
        self.assertEqual(self.client.get(MINE).status_code, 401)
        self.login_as("recruiter", "r2@example.com")
        self.assertEqual(self.client.get(MINE).status_code, 403)

    def test_deleting_a_resume_keeps_the_application(self):
        candidate = self.candidate("a@example.com")
        self.client.post(APPLY, {"job": self.job1.pk}, format="json")
        Resume.objects.filter(candidate=candidate).delete()
        res = self.client.get(MINE)
        self.assertEqual(res.data["count"], 1)
        self.assertIsNone(res.data["results"][0]["resume"])

    def test_deleting_a_candidate_removes_their_applications(self):
        user = self.login_as("candidate", "gone@example.com")
        make_resume(Candidate.objects.get(user=user))
        self.client.post(APPLY, {"job": self.job1.pk}, format="json")
        self.assertEqual(Application.objects.count(), 1)
        user.delete()
        self.assertEqual(Application.objects.count(), 0)
        self.assertTrue(Job.objects.filter(pk=self.job1.pk).exists())


class DeletingJobsWithApplicationsTests(LoginMixin, APITestCase):
    def setUp(self):
        self.login_as("recruiter", "owner@example.com")
        res = self.client.post(
            "/api/jobs/manage/",
            {"job_title": "Backend Developer", "company_name": "Acme", "location": "Pune",
             "description": "We are looking for a motivated engineer to build and ship AI features with the team."},
            format="json",
        )
        self.job_id = res.data["id"]

    def candidate_applies(self):
        user = self.login_as("candidate", "cand@example.com")
        make_resume(Candidate.objects.get(user=user))
        self.assertEqual(self.client.post(APPLY, {"job": self.job_id}, format="json").status_code, 201)
        self.login_as("recruiter", "owner@example.com")

    def test_job_without_applications_can_be_deleted(self):
        res = self.client.delete(f"/api/jobs/manage/{self.job_id}/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Job.objects.filter(pk=self.job_id).exists())

    def test_job_with_applications_cannot_be_deleted(self):
        self.candidate_applies()
        res = self.client.delete(f"/api/jobs/manage/{self.job_id}/")
        self.assertEqual(res.status_code, 409)
        self.assertIn("Unpublish", res.data["message"])
        self.assertTrue(Job.objects.filter(pk=self.job_id).exists())
        self.assertEqual(Application.objects.count(), 1)

    def test_job_with_applications_can_be_unpublished_instead(self):
        self.candidate_applies()
        res = self.client.patch(f"/api/jobs/manage/{self.job_id}/", {"is_active": False}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["is_active"])
        self.assertEqual(Application.objects.count(), 1)