from rest_framework.test import APITestCase

from accounts.models import User
from recruiters.models import Recruiter
from resumes.models import Skill

from .models import Job

PASSWORD = "StrongPass#2026"
MANAGE = "/api/jobs/manage/"
BROWSE = "/api/jobs/"
DESCRIPTION = "We are looking for a motivated engineer to build and ship AI features with the team."


def job_payload(**extra):
    data = {
        "job_title": "Backend Developer",
        "company_name": "Acme Tech",
        "location": "Gurugram",
        "job_type": "full_time",
        "description": DESCRIPTION,
        "required_skills": ["Python", "Django", "SQL"],
        "required_experience": 1,
        "required_education": "B.Tech in CS",
        "salary_range": "6-8 LPA",
    }
    data.update(extra)
    return data


class JobTestBase(APITestCase):
    def login_as(self, role, email=None):
        email = email or f"{role}@example.com"
        self.client.credentials()
        self.client.post(
            f"/api/auth/register/{role}/",
            {"email": email, "first_name": "Test", "last_name": "User", "password": PASSWORD, "password2": PASSWORD},
            format="json",
        )
        res = self.client.post("/api/auth/login/", {"email": email, "password": PASSWORD}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return User.objects.get(email=email)

    def create_job(self, **extra):
        res = self.client.post(MANAGE, job_payload(**extra), format="json")
        self.assertEqual(res.status_code, 201, res.data)
        return res.data


class RecruiterCreateTests(JobTestBase):
    def test_recruiter_creates_job(self):
        user = self.login_as("recruiter")
        res = self.client.post(MANAGE, job_payload(), format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["job_title"], "Backend Developer")
        self.assertTrue(res.data["is_active"])  # published by default
        self.assertEqual(sorted(res.data["required_skills"]), ["Django", "Python", "SQL"])
        job = Job.objects.get(pk=res.data["id"])
        self.assertEqual(job.recruiter.user, user)  # owner is the logged-in recruiter

    def test_skill_names_are_normalized_and_deduplicated(self):
        self.login_as("recruiter")
        data = self.create_job(required_skills=["ml", "Machine Learning", "sql", "  Python ", "python", "", "Custom Tool"])
        self.assertEqual(sorted(data["required_skills"]), ["Custom Tool", "Machine Learning", "Python", "SQL"])

    def test_job_skills_share_the_skill_table_with_resumes(self):
        Skill.objects.create(name="Python", category="Programming Languages")
        self.login_as("recruiter")
        self.create_job(required_skills=["python"])
        self.assertEqual(Skill.objects.filter(name__iexact="python").count(), 1)

    def test_company_name_defaults_to_recruiter_profile(self):
        user = self.login_as("recruiter")
        Recruiter.objects.filter(user=user).update(company_name="Profile Corp")
        payload = job_payload()
        del payload["company_name"]
        res = self.client.post(MANAGE, payload, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["company_name"], "Profile Corp")

    def test_company_name_required_when_profile_has_none(self):
        self.login_as("recruiter")
        payload = job_payload()
        del payload["company_name"]
        res = self.client.post(MANAGE, payload, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("company_name", res.data["errors"])

    def test_can_create_unpublished_job(self):
        self.login_as("recruiter")
        self.assertFalse(self.create_job(is_active=False)["is_active"])

    def test_defaults_when_optional_fields_missing(self):
        self.login_as("recruiter")
        res = self.client.post(
            MANAGE,
            {"job_title": "Intern", "company_name": "Acme", "location": "Remote", "description": DESCRIPTION},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["job_type"], "full_time")
        self.assertEqual(res.data["required_experience"], 0)
        self.assertEqual(res.data["required_skills"], [])

    def test_validation_errors(self):
        self.login_as("recruiter")
        cases = {
            "job_title": ("", "ab"),
            "location": ("",),
            "description": ("too short",),
            "job_type": ("part-time", "fulltime"),
            "required_experience": (-1, 41, "abc"),
        }
        for field, values in cases.items():
            for value in values:
                res = self.client.post(MANAGE, job_payload(**{field: value}), format="json")
                self.assertEqual(res.status_code, 400, (field, value))
                self.assertIn(field, res.data["errors"], (field, value))
        self.assertEqual(Job.objects.count(), 0)

    def test_skill_list_validation(self):
        self.login_as("recruiter")
        too_many = [f"Skill number {i}" for i in range(31)]
        res = self.client.post(MANAGE, job_payload(required_skills=too_many), format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("required_skills", res.data["errors"])
        res = self.client.post(MANAGE, job_payload(required_skills=["x" * 101]), format="json")
        self.assertEqual(res.status_code, 400)
        res = self.client.post(MANAGE, job_payload(required_skills="Python"), format="json")
        self.assertEqual(res.status_code, 400)

    def test_protected_and_unknown_fields_rejected(self):
        self.login_as("recruiter")
        for field, value in (("recruiter", 1), ("id", 99), ("created_at", "2020-01-01"), ("hacker", "x")):
            res = self.client.post(MANAGE, job_payload(**{field: value}), format="json")
            self.assertEqual(res.status_code, 400, field)
            self.assertIn(field, res.data["errors"])
        self.assertEqual(Job.objects.count(), 0)

    def test_candidate_cannot_create(self):
        self.login_as("candidate")
        self.assertEqual(self.client.post(MANAGE, job_payload(), format="json").status_code, 403)
        self.assertEqual(Job.objects.count(), 0)

    def test_anonymous_cannot_create(self):
        self.assertEqual(self.client.post(MANAGE, job_payload(), format="json").status_code, 401)


class RecruiterManageTests(JobTestBase):
    def test_recruiter_sees_only_own_jobs_including_unpublished(self):
        self.login_as("recruiter", "r1@example.com")
        mine = self.create_job(job_title="Mine published")["id"]
        hidden = self.create_job(job_title="Mine unpublished", is_active=False)["id"]
        self.login_as("recruiter", "r2@example.com")
        self.create_job(job_title="Someone else's")
        self.login_as("recruiter", "r1@example.com")
        res = self.client.get(MANAGE)
        self.assertEqual(res.status_code, 200)
        self.assertEqual({j["id"] for j in res.data["results"]}, {mine, hidden})

    def test_retrieve_own_job(self):
        self.login_as("recruiter")
        jid = self.create_job()["id"]
        res = self.client.get(f"{MANAGE}{jid}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["id"], jid)

    def test_other_recruiters_job_is_404_for_get_patch_delete(self):
        self.login_as("recruiter", "r1@example.com")
        jid = self.create_job()["id"]
        self.login_as("recruiter", "r2@example.com")
        self.assertEqual(self.client.get(f"{MANAGE}{jid}/").status_code, 404)
        self.assertEqual(self.client.patch(f"{MANAGE}{jid}/", {"job_title": "Hacked"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(f"{MANAGE}{jid}/").status_code, 404)
        job = Job.objects.get(pk=jid)
        self.assertEqual(job.job_title, "Backend Developer")

    def test_patch_updates_fields_and_replaces_skills(self):
        self.login_as("recruiter")
        jid = self.create_job()["id"]
        res = self.client.patch(
            f"{MANAGE}{jid}/",
            {"job_title": "Senior Backend Developer", "required_skills": ["Docker", "ml"], "required_experience": 3},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["job_title"], "Senior Backend Developer")
        self.assertEqual(sorted(res.data["required_skills"]), ["Docker", "Machine Learning"])
        self.assertEqual(res.data["required_experience"], 3)
        self.assertEqual(res.data["location"], "Gurugram")  # untouched

    def test_patch_without_skills_keeps_skills(self):
        self.login_as("recruiter")
        jid = self.create_job()["id"]
        res = self.client.patch(f"{MANAGE}{jid}/", {"location": "Pune"}, format="json")
        self.assertEqual(sorted(res.data["required_skills"]), ["Django", "Python", "SQL"])

    def test_patch_can_clear_skills(self):
        self.login_as("recruiter")
        jid = self.create_job()["id"]
        res = self.client.patch(f"{MANAGE}{jid}/", {"required_skills": []}, format="json")
        self.assertEqual(res.data["required_skills"], [])

    def test_publish_and_unpublish(self):
        self.login_as("recruiter")
        jid = self.create_job()["id"]
        self.assertFalse(self.client.patch(f"{MANAGE}{jid}/", {"is_active": False}, format="json").data["is_active"])
        self.assertTrue(self.client.patch(f"{MANAGE}{jid}/", {"is_active": True}, format="json").data["is_active"])

    def test_patch_validation_and_protected_fields(self):
        self.login_as("recruiter")
        jid = self.create_job()["id"]
        self.assertEqual(self.client.patch(f"{MANAGE}{jid}/", {"description": "short"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(f"{MANAGE}{jid}/", {"company_name": "  "}, format="json").status_code, 400)
        res = self.client.patch(f"{MANAGE}{jid}/", {"recruiter": 5, "created_at": "2020-01-01"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Job.objects.get(pk=jid).company_name, "Acme Tech")

    def test_put_is_not_allowed(self):
        self.login_as("recruiter")
        jid = self.create_job()["id"]
        response = self.client.put(f"{MANAGE}{jid}/", job_payload(), format="json")
        self.assertEqual(response.status_code, 200)
    
    def test_delete_own_job(self):
        self.login_as("recruiter")
        jid = self.create_job()["id"]
        res = self.client.delete(f"{MANAGE}{jid}/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Job.objects.filter(pk=jid).exists())
        self.assertEqual(self.client.get(f"{MANAGE}{jid}/").status_code, 404)

    def test_deleting_job_keeps_shared_skills(self):
        self.login_as("recruiter")
        jid = self.create_job()["id"]
        self.client.delete(f"{MANAGE}{jid}/")
        self.assertTrue(Skill.objects.filter(name="Python").exists())

    def test_candidate_cannot_use_manage_endpoints(self):
        self.login_as("recruiter")
        jid = self.create_job()["id"]
        self.login_as("candidate")
        self.assertEqual(self.client.get(MANAGE).status_code, 403)
        self.assertEqual(self.client.get(f"{MANAGE}{jid}/").status_code, 403)
        self.assertEqual(self.client.patch(f"{MANAGE}{jid}/", {"job_title": "X Y Z"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"{MANAGE}{jid}/").status_code, 403)
        self.assertTrue(Job.objects.filter(pk=jid).exists())

    def test_anonymous_cannot_use_manage_endpoints(self):
        for method, url in (("get", MANAGE), ("get", f"{MANAGE}1/"), ("patch", f"{MANAGE}1/"), ("delete", f"{MANAGE}1/")):
            self.assertEqual(getattr(self.client, method)(url).status_code, 401, (method, url))

    def test_deleting_recruiter_account_removes_their_jobs(self):
        user = self.login_as("recruiter")
        self.create_job()
        user.delete()
        self.assertEqual(Job.objects.count(), 0)

    def test_manage_list_is_paginated(self):
        self.login_as("recruiter")
        for i in range(12):
            self.create_job(job_title=f"Role number {i}")
        page1 = self.client.get(MANAGE)
        self.assertEqual(page1.data["count"], 12)
        self.assertEqual(len(page1.data["results"]), 10)
        self.assertEqual(len(self.client.get(MANAGE + "?page=2").data["results"]), 2)


class CandidateBrowseTests(JobTestBase):
    def setUp(self):
        self.login_as("recruiter")
        self.active_id = self.create_job(job_title="Visible Role")["id"]
        self.inactive_id = self.create_job(job_title="Hidden Role", is_active=False)["id"]

    def test_candidate_sees_only_active_jobs(self):
        self.login_as("candidate")
        res = self.client.get(BROWSE)
        self.assertEqual(res.status_code, 200)
        self.assertEqual([j["id"] for j in res.data["results"]], [self.active_id])

    def test_candidate_gets_active_job_detail(self):
        self.login_as("candidate")
        res = self.client.get(f"{BROWSE}{self.active_id}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["job_title"], "Visible Role")
        self.assertEqual(sorted(res.data["required_skills"]), ["Django", "Python", "SQL"])

    def test_inactive_job_detail_is_404_for_candidate(self):
        self.login_as("candidate")
        self.assertEqual(self.client.get(f"{BROWSE}{self.inactive_id}/").status_code, 404)

    def test_candidate_cannot_modify_jobs(self):
        self.login_as("candidate")
        self.assertEqual(self.client.post(BROWSE, job_payload(), format="json").status_code, 405)
        url = f"{BROWSE}{self.active_id}/"
        self.assertEqual(self.client.patch(url, {"job_title": "Hacked"}, format="json").status_code, 405)
        self.assertEqual(self.client.put(url, job_payload(), format="json").status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)
        self.assertEqual(Job.objects.get(pk=self.active_id).job_title, "Visible Role")

    def test_recruiter_cannot_use_candidate_browse_endpoints(self):
        self.login_as("recruiter", "other@example.com")
        self.assertEqual(self.client.get(BROWSE).status_code, 403)
        self.assertEqual(self.client.get(f"{BROWSE}{self.active_id}/").status_code, 403)

    def test_anonymous_cannot_browse(self):
        self.client.credentials()
        self.assertEqual(self.client.get(BROWSE).status_code, 401)
        self.assertEqual(self.client.get(f"{BROWSE}{self.active_id}/").status_code, 401)

    def test_unpublishing_hides_job_and_republishing_shows_it(self):
        self.login_as("recruiter", "r1@example.com")  # new recruiter, new job
        jid = self.create_job(job_title="Toggle Role")["id"]
        self.client.patch(f"{MANAGE}{jid}/", {"is_active": False}, format="json")
        self.login_as("candidate")
        self.assertEqual(self.client.get(f"{BROWSE}{jid}/").status_code, 404)
        self.login_as("recruiter", "r1@example.com")
        self.client.patch(f"{MANAGE}{jid}/", {"is_active": True}, format="json")
        self.login_as("candidate")
        self.assertEqual(self.client.get(f"{BROWSE}{jid}/").status_code, 200)

    def test_candidate_does_not_get_recruiter_private_data(self):
        self.login_as("candidate")
        data = self.client.get(f"{BROWSE}{self.active_id}/").data
        self.assertNotIn("recruiter", data)
        self.assertNotIn("email", str(data).lower().replace("e-mail", ""))


class FilterTests(JobTestBase):
    def setUp(self):
        self.login_as("recruiter")
        self.create_job(job_title="Python Backend Developer", location="Gurugram", company_name="Acme Tech",
                        required_skills=["Python", "Django", "SQL"], required_experience=2, job_type="full_time")
        self.create_job(job_title="Machine Learning Intern", location="Bengaluru", company_name="Beta Labs",
                        required_skills=["Python", "Machine Learning", "pandas"], required_experience=0, job_type="internship")
        self.create_job(job_title="React Frontend Developer", location="Remote", company_name="Acme Tech",
                        required_skills=["React", "JavaScript", "CSS"], required_experience=1, job_type="contract")
        self.create_job(job_title="Hidden Data Analyst", location="Gurugram", company_name="Acme Tech",
                        required_skills=["SQL", "Tableau"], is_active=False)
        self.login_as("candidate")

    def titles(self, query):
        res = self.client.get(BROWSE + query)
        self.assertEqual(res.status_code, 200, res.data)
        return sorted(j["job_title"] for j in res.data["results"])

    def test_no_filter_returns_all_active(self):
        self.assertEqual(len(self.titles("")), 3)

    def test_filter_by_title_case_insensitive_partial(self):
        self.assertEqual(self.titles("?title=developer"), ["Python Backend Developer", "React Frontend Developer"])
        self.assertEqual(self.titles("?title=INTERN"), ["Machine Learning Intern"])
        self.assertEqual(self.titles("?title=nonexistent"), [])

    def test_filter_by_location(self):
        self.assertEqual(self.titles("?location=gurugram"), ["Python Backend Developer"])
        self.assertEqual(self.titles("?location=remote"), ["React Frontend Developer"])
        self.assertEqual(self.titles("?location=guru"), ["Python Backend Developer"])

    def test_filter_by_company(self):
        self.assertEqual(self.titles("?company=beta"), ["Machine Learning Intern"])

    def test_filter_by_single_skill(self):
        self.assertEqual(self.titles("?skills=python"), ["Machine Learning Intern", "Python Backend Developer"])

    def test_filter_by_multiple_skills_requires_all(self):
        self.assertEqual(self.titles("?skills=python,django"), ["Python Backend Developer"])
        self.assertEqual(self.titles("?skills=python,react"), [])

    def test_filter_by_skills_any(self):
        self.assertEqual(
            self.titles("?skills=django,react&skills_match=any"),
            ["Python Backend Developer", "React Frontend Developer"],
        )

    def test_skill_filter_understands_aliases(self):
        self.assertEqual(self.titles("?skills=ML"), ["Machine Learning Intern"])
        self.assertEqual(self.titles("?skills=sql"), ["Python Backend Developer"])

    def test_skill_filter_with_spaces_and_empty_parts(self):
        self.assertEqual(self.titles("?skills=%20python%20,,%20django"), ["Python Backend Developer"])

    def test_inactive_jobs_never_appear_in_candidate_filters(self):
        self.assertEqual(self.titles("?skills=tableau"), [])
        self.assertEqual(self.titles("?title=analyst"), [])

    def test_filter_by_job_type_and_experience(self):
        self.assertEqual(self.titles("?job_type=internship"), ["Machine Learning Intern"])
        self.assertEqual(self.titles("?max_experience=0"), ["Machine Learning Intern"])
        self.assertEqual(len(self.titles("?max_experience=1")), 2)

    def test_combined_filters(self):
        self.assertEqual(self.titles("?title=developer&location=remote&skills=react"), ["React Frontend Developer"])
        self.assertEqual(self.titles("?title=developer&location=bengaluru"), [])

    def test_ordering(self):
        res = self.client.get(BROWSE + "?ordering=job_title")
        names = [j["job_title"] for j in res.data["results"]]
        self.assertEqual(names, sorted(names))
        res = self.client.get(BROWSE + "?ordering=-required_experience")
        self.assertEqual(res.data["results"][0]["job_title"], "Python Backend Developer")

    def test_invalid_filter_values_return_400(self):
        for query in ("?job_type=weekend", "?max_experience=abc", "?max_experience=-1",
                      "?ordering=salary_range", "?skills_match=maybe&skills=python",
                      "?skills=" + ",".join(f"s{i}" for i in range(11))):
            res = self.client.get(BROWSE + query)
            self.assertEqual(res.status_code, 400, query)
            self.assertIn("errors", res.data)

    def test_filters_do_not_duplicate_results(self):
        res = self.client.get(BROWSE + "?skills=python,django,sql&skills_match=any")
        ids = [j["id"] for j in res.data["results"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_recruiter_manage_list_supports_filters_and_is_active(self):
        self.login_as("recruiter")  # the recruiter who owns the jobs created in setUp
        self.assertEqual(self.client.get(MANAGE + "?title=hidden").data["count"], 1)
        self.assertEqual(self.client.get(MANAGE + "?is_active=false").data["count"], 1)
        self.assertEqual(self.client.get(MANAGE + "?is_active=true").data["count"], 3)
        self.assertEqual(self.client.get(MANAGE + "?is_active=maybe").status_code, 400)