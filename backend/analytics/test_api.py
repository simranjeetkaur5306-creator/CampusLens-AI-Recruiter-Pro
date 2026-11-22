from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from applications.models import Application
from matching.factories import LoginMixin, make_candidate, make_job, make_recruiter, make_resume, set_embedding, vector
from recruiters.models import Recruiter

URL = "/api/analytics/recruiter/overview/"
OWNER = "owner@example.com"


class Base(LoginMixin, APITestCase):
    """The owner has two jobs; another recruiter has one. Only the owner's data may be counted."""

    def setUp(self):
        owner_user = self.login_as("recruiter", OWNER)
        self.owner = Recruiter.objects.get(user=owner_user)
        self.job_a = make_job(self.owner, title="ML Engineer", skills=("Python", "SQL", "Machine Learning"))
        self.job_b = make_job(self.owner, title="Backend Developer", skills=("Python",), active=False)
        self.foreign_job = make_job(make_recruiter("other@example.com"), title="Foreign", skills=("Rust",))
        self.n = 0

    def apply(self, job, skills, status="applied", vec=None):
        self.n += 1
        candidate = make_candidate(f"cand{self.n}@example.com")
        resume = make_resume(candidate, skills=skills)
        if vec is not None:
            set_embedding(resume, vec)
        return Application.objects.create(candidate=candidate, job=job, resume=resume, status=status)

    def overview(self, **params):
        self.client.credentials()
        self.login_as("recruiter", OWNER)
        return self.client.get(URL, params)


class AccessTests(Base):
    def test_only_recruiters_can_read_it(self):
        self.login_as("candidate", "someone@example.com")
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_bad_days_are_rejected(self):
        for bad in ("3", "500", "abc", "-5", "7.5"):
            self.assertEqual(self.overview(days=bad).status_code, 400, bad)
        self.assertEqual(self.overview(days="7").status_code, 200)
        self.assertEqual(self.overview(days="90").status_code, 200)


class EmptyStateTests(Base):
    def test_a_recruiter_without_applications_gets_zeros_not_errors(self):
        res = self.overview()
        self.assertEqual(res.status_code, 200)
        totals = res.data["totals"]
        self.assertEqual((totals["jobs_posted"], totals["applications"], totals["shortlisted"]), (2, 0, 0))
        self.assertEqual([row["count"] for row in res.data["status_distribution"]], [0, 0, 0, 0])
        self.assertIsNone(res.data["matching"]["average_score"])
        self.assertEqual(res.data["top_candidate_skills"], [])
        self.assertEqual(res.data["common_skill_gaps"]["items"], [])
        self.assertEqual(len(res.data["jobs"]), 2)


class OverviewTests(Base):
    def setUp(self):
        super().setUp()
        self.a1 = self.apply(self.job_a, ("Python", "SQL"), vec=vector(1, 0))
        self.a2 = self.apply(self.job_a, ("Python",), status="shortlisted", vec=vector(0, 1))
        self.a3 = self.apply(self.job_b, ("Python", "Django"), status="rejected")
        self.apply(self.foreign_job, ("Rust",), status="shortlisted", vec=vector(1, 0))  # not the owner's
        set_embedding(self.job_a, vector(1, 0))

    def test_totals_ignore_other_recruiters(self):
        totals = self.overview().data["totals"]
        self.assertEqual(totals["jobs_posted"], 2)
        self.assertEqual(totals["jobs_published"], 1)
        self.assertEqual(totals["applications"], 3)
        self.assertEqual(totals["awaiting_review"], 1)
        self.assertEqual(totals["shortlisted"], 1)
        self.assertEqual(totals["rejected"], 1)
        self.assertEqual(totals["interviews_scheduled"], 0)

    def test_status_distribution_lists_every_status(self):
        Application.objects.filter(pk=self.a1.pk).update(status="interview_scheduled")
        rows = self.overview().data["status_distribution"]
        self.assertEqual([r["status"] for r in rows], ["applied", "shortlisted", "rejected", "interview_scheduled"])
        self.assertEqual([r["count"] for r in rows], [0, 1, 1, 1])
        self.assertEqual(rows[3]["label"], "Interview scheduled")

    def test_applications_over_time_is_zero_filled(self):
        res = self.overview(days="7")
        series = res.data["applications_over_time"]
        self.assertEqual(series["days"], 7)
        self.assertEqual(len(series["points"]), 7)
        self.assertEqual(series["points"][-1], {"date": timezone.localdate().isoformat(), "count": 3})
        self.assertEqual(sum(p["count"] for p in series["points"]), 3)
        self.assertEqual(len(self.overview().data["applications_over_time"]["points"]), 30)

    def test_old_applications_fall_outside_the_window(self):
        Application.objects.filter(pk=self.a3.pk).update(applied_at=timezone.now() - timedelta(days=40))
        points = self.overview(days="30").data["applications_over_time"]["points"]
        self.assertEqual(sum(p["count"] for p in points), 2)
        self.assertEqual(self.overview().data["totals"]["applications"], 3)  # totals still count it

    def test_top_candidate_skills(self):
        rows = self.overview().data["top_candidate_skills"]
        self.assertEqual(rows[0], {"skill": "Python", "count": 3})
        self.assertEqual([(r["skill"], r["count"]) for r in rows[1:]], [("Django", 1), ("SQL", 1)])
        self.assertNotIn("Rust", [r["skill"] for r in rows])

    def test_common_skill_gaps(self):
        gaps = self.overview().data["common_skill_gaps"]
        self.assertEqual(gaps["analysed_applications"], 3)
        items = {row["skill"]: row for row in gaps["items"]}
        self.assertEqual(items["Machine Learning"]["count"], 2)   # a1 and a2 lack it
        self.assertEqual(items["Machine Learning"]["share_percent"], 66.7)
        self.assertEqual(items["SQL"]["count"], 1)                # only a2 lacks it
        self.assertNotIn("Python", items)                         # everyone has it
        self.assertNotIn("Rust", items)

    def test_average_match_uses_only_scored_applications(self):
        data = self.overview().data
        self.assertEqual(data["matching"]["scored_applications"], 2)
        self.assertEqual(data["matching"]["total_applications"], 3)
        self.assertEqual(data["matching"]["average_score"], 50.0)  # similarities 1.0 and 0.0
        by_id = {row["id"]: row for row in data["jobs"]}
        self.assertEqual(by_id[self.job_a.pk]["average_score"], 50.0)
        self.assertIsNone(by_id[self.job_b.pk]["average_score"])  # job_b has no vector

    def test_per_job_counts(self):
        by_id = {row["id"]: row for row in self.overview().data["jobs"]}
        a = by_id[self.job_a.pk]
        self.assertEqual((a["applications"], a["awaiting_review"], a["shortlisted"], a["rejected"]), (2, 1, 1, 0))
        b = by_id[self.job_b.pk]
        self.assertEqual((b["applications"], b["rejected"], b["is_active"]), (1, 1, False))
        self.assertNotIn(self.foreign_job.pk, by_id)

    def test_changing_a_status_changes_the_numbers(self):
        self.client.credentials()
        self.login_as("recruiter", OWNER)
        self.client.patch(f"/api/applications/{self.a1.pk}/status/", {"status": "shortlisted"}, format="json")
        totals = self.client.get(URL).data["totals"]
        self.assertEqual((totals["shortlisted"], totals["awaiting_review"]), (2, 0))

    def test_response_exposes_no_personal_data(self):
        text = str(self.overview().data)
        self.assertNotIn("cand1@example.com", text)
        self.assertNotIn("extracted_text", text)