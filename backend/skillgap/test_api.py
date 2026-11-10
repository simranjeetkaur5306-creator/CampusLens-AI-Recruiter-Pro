from rest_framework.test import APITestCase

from applications.models import Application
from candidates.models import Candidate
from jobs.models import Job
from matching.factories import LoginMixin, make_candidate, make_job, make_recruiter, make_resume
from matching.services import ranking
from resumes.models import Resume

URL = "/api/skill-gap/jobs/{}/"


class SkillGapAPITests(LoginMixin, APITestCase):
    def setUp(self):
        self.recruiter = make_recruiter()
        self.job = make_job(self.recruiter, title="Backend Developer", skills=("Python", "Django", "SQL", "Docker"))
        user = self.login_as("candidate", "cand@example.com")
        self.candidate = Candidate.objects.get(user=user)
        self.resume = make_resume(
            self.candidate, skills=("Python", "PostgreSQL"), text="Built REST APIs with Python and PostgreSQL."
        )

    def get(self, job=None, **params):
        return self.client.get(URL.format((job or self.job).pk), params)

    def test_analysis_of_the_active_resume(self):
        res = self.get()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["job"]["job_title"], "Backend Developer")
        self.assertEqual(res.data["resume"], {"id": self.resume.pk, "original_filename": "x.pdf", "is_active": True})
        self.assertEqual([r["skill"] for r in res.data["matched"]], ["Python"])
        self.assertEqual([r["skill"] for r in res.data["partial"]], ["SQL"])
        self.assertEqual([r["skill"] for r in res.data["missing"]], ["Django", "Docker"])
        self.assertEqual(
            (res.data["total_required"], res.data["matched_count"], res.data["partial_count"], res.data["missing_count"]),
            (4, 1, 1, 2),
        )
        self.assertEqual(res.data["coverage_percent"], 37.5)  # (1 + 0.5) / 4
        self.assertIn("0.5", res.data["coverage_rule"])
        self.assertEqual(res.data["summary"], "Your resume covers 1 of 4 required skills, partly covers 1, and 2 could not be found.")
        self.assertIn("did not write on your resume", res.data["disclaimer"])

    def test_partial_evidence_explains_itself(self):
        sql = self.get().data["partial"][0]
        self.assertEqual(sql["evidence"]["type"], "implied")
        self.assertEqual(sql["evidence"]["skills"], ["PostgreSQL"])
        self.assertIn("PostgreSQL", sql["evidence"]["note"])

    def test_learning_plan(self):
        plan = self.get().data["learning_plan"]
        self.assertEqual([(p["priority"], p["skill"], p["status"]) for p in plan],
                         [(1, "Django", "missing"), (2, "Docker", "missing"), (3, "SQL", "partial")])
        for step in plan:
            self.assertTrue(step["topics"])
            self.assertTrue(step["project_idea"])
            self.assertIn(step["source"], ("curated", "generic"))
        self.assertEqual(plan[0]["learn_after"], [])  # the candidate already has Python

    def test_agrees_with_the_applicant_ranking_skill_comparison(self):
        res = self.get().data
        resume_skills = [s.name for s in self.resume.skills.all()]
        job_skills = [s.name for s in self.job.required_skills.all()]
        literal_matching, literal_missing = ranking.skill_overlap(resume_skills, job_skills)
        self.assertEqual([r["skill"] for r in res["matched"]], literal_matching)
        self.assertEqual(sorted(r["skill"] for r in res["partial"] + res["missing"]), literal_missing)

    def test_another_of_my_resumes_can_be_analysed(self):
        Resume.objects.filter(pk=self.resume.pk).update(is_active=False)
        older = make_resume(self.candidate, skills=("Django", "Docker"), active=False)
        res = self.get(resume_id=older.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["resume"]["id"], older.pk)
        self.assertFalse(res.data["resume"]["is_active"])
        self.assertEqual([r["skill"] for r in res.data["matched"]], ["Django", "Docker"])

    def test_resume_id_must_belong_to_me_and_be_parsed(self):
        other = make_resume(make_candidate("other@example.com"))
        self.assertEqual(self.get(resume_id=other.pk).status_code, 404)
        self.assertEqual(self.get(resume_id=999999).status_code, 404)
        self.assertEqual(self.get(resume_id="abc").status_code, 400)
        failed = make_resume(self.candidate, status="failed", active=False)
        res = self.get(resume_id=failed.pk)
        self.assertEqual(res.status_code, 400)
        self.assertIn("resume_id", res.data["errors"])

    def test_a_resume_is_required(self):
        Resume.objects.all().delete()
        res = self.get()
        self.assertEqual(res.status_code, 400)
        self.assertIn("resume", res.data["errors"])
        make_resume(self.candidate, status="failed", active=True)  # active but not parsed
        self.assertEqual(self.get().status_code, 400)

    def test_closed_jobs_are_hidden_unless_the_candidate_applied(self):
        closed = make_job(self.recruiter, title="Closed role", active=False, skills=("Python",))
        self.assertEqual(self.get(closed).status_code, 404)
        Application.objects.create(candidate=self.candidate, job=closed, resume=self.resume)
        self.assertEqual(self.get(closed).status_code, 200)

    def test_unknown_job(self):
        self.assertEqual(self.client.get(URL.format(999999)).status_code, 404)

    def test_only_candidates_can_use_it(self):
        self.login_as("recruiter", "rec@example.com")
        self.assertEqual(self.get().status_code, 403)
        self.client.credentials()
        self.assertEqual(self.get().status_code, 401)

    def test_read_only(self):
        self.assertEqual(self.client.post(URL.format(self.job.pk), {}, format="json").status_code, 405)

    def test_job_without_required_skills(self):
        bare = make_job(self.recruiter, title="Bare job", skills=())
        res = self.get(bare)
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.data["total_required"], res.data["coverage_percent"], res.data["learning_plan"]), (0, None, []))

    def test_a_skill_outside_the_dictionary_is_found_in_the_resume_text(self):
        job = make_job(self.recruiter, title="Odd job", skills=("Quantum Weaving",))
        Resume.objects.filter(pk=self.resume.pk).update(extracted_text="Led a quantum weaving club at college.")
        res = self.get(job)
        self.assertEqual([r["skill"] for r in res.data["matched"]], ["Quantum Weaving"])
        self.assertEqual(res.data["matched"][0]["evidence"]["type"], "mentioned_in_text")

    def test_no_resume_text_or_private_data_is_sent(self):
        text = str(self.get().data)
        for forbidden in ("embedding", "extracted_text", "Built REST APIs", "r@example.com"):
            self.assertNotIn(forbidden, text)

    def test_the_analysis_changes_nothing(self):
        before = (Resume.objects.count(), Job.objects.count(), Application.objects.count())
        self.get()
        self.assertEqual(before, (Resume.objects.count(), Job.objects.count(), Application.objects.count()))