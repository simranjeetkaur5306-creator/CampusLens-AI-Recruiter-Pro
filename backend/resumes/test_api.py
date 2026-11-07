import os
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import User
from candidates.models import Candidate

from .models import Resume, Skill
from .test_extraction import SAMPLE_RESUME
from .test_files import make_docx, make_pdf

PASSWORD = "StrongPass#2026"
UPLOAD_URL = "/api/resumes/upload/"
LIST_URL = "/api/resumes/"
ME_URL = "/api/resumes/me/"

TEST_MEDIA = tempfile.mkdtemp(prefix="campuslens_test_media_")


def pdf_file(name="resume.pdf", text=SAMPLE_RESUME):
    return SimpleUploadedFile(name, make_pdf(text), content_type="application/pdf")


def docx_file(name="resume.docx"):
    data = make_docx(SAMPLE_RESUME.split("\n"))
    return SimpleUploadedFile(name, data, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@override_settings(MEDIA_ROOT=TEST_MEDIA)
class ResumeAPITests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA, ignore_errors=True)

    # ---------- helpers ----------
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

    def upload(self, file):
        return self.client.post(UPLOAD_URL, {"file": file}, format="multipart")

    def media_files(self):
        found = []
        for folder, _dirs, files in os.walk(TEST_MEDIA):
            found.extend(os.path.join(folder, f) for f in files)
        return found

    def setUp(self):
        for path in self.media_files():
            os.remove(path)

    # ---------- uploads ----------
    def test_pdf_upload_success(self):
        user = self.login_as("candidate")
        res = self.upload(pdf_file())
        self.assertEqual(res.status_code, 201)
        resume = res.data["resume"]
        self.assertEqual(resume["parsing_status"], "success")
        self.assertTrue(resume["is_active"])
        self.assertEqual(resume["original_filename"], "resume.pdf")
        skills = {s["name"] for s in resume["skills"]}
        self.assertTrue({"Python", "SQL", "Machine Learning", "Django", "Docker"} <= skills)
        self.assertEqual(resume["contact"]["email"], "simran.kaur@example.com")
        self.assertEqual(resume["contact"]["name"], "Simran Kaur")
        self.assertTrue(len(resume["education"]) >= 1)
        self.assertEqual(len(resume["experience"]), 1)
        self.assertEqual([p["title"] for p in resume["projects"]], ["PulseIQ", "CampusLens AI"])
        self.assertEqual(len(resume["certifications"]), 2)

        # stored under a random name in the user's folder, not under the uploaded name
        stored = Resume.objects.get(pk=resume["id"]).file.name
        self.assertTrue(stored.startswith(f"resumes/{user.id}/"))
        self.assertNotIn("resume.pdf", stored)
        self.assertEqual(len(self.media_files()), 1)

    def test_docx_upload_success(self):
        self.login_as("candidate")
        res = self.upload(docx_file())
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["resume"]["file_type"], "docx")
        self.assertEqual(res.data["resume"]["parsing_status"], "success")
        self.assertIn("Python", {s["name"] for s in res.data["resume"]["skills"]})

    def test_invalid_file_type_rejected(self):
        self.login_as("candidate")
        res = self.upload(SimpleUploadedFile("notes.txt", b"hello"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("file", res.data["errors"])
        self.assertEqual(Resume.objects.count(), 0)
        self.assertEqual(self.media_files(), [])

    def test_fake_pdf_rejected(self):
        self.login_as("candidate")
        res = self.upload(SimpleUploadedFile("resume.pdf", b"plain text pretending to be a pdf"))
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Resume.objects.count(), 0)

    def test_corrupted_documents_rejected(self):
        self.login_as("candidate")
        broken_pdf = b"%PDF-1.4\n" + b"broken body " * 100
        self.assertEqual(self.upload(SimpleUploadedFile("a.pdf", broken_pdf)).status_code, 400)
        self.assertEqual(self.upload(SimpleUploadedFile("b.docx", b"PK\x03\x04" + b"junk" * 50)).status_code, 400)
        self.assertEqual(Resume.objects.count(), 0)
        self.assertEqual(self.media_files(), [])

    def test_file_larger_than_5mb_rejected(self):
        self.login_as("candidate")
        big = b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024 + 10)
        res = self.upload(SimpleUploadedFile("big.pdf", big))
        self.assertEqual(res.status_code, 400)
        self.assertIn("too large", res.data["errors"]["file"][0])
        self.assertEqual(Resume.objects.count(), 0)

    def test_missing_file_field(self):
        self.login_as("candidate")
        res = self.client.post(UPLOAD_URL, {}, format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertIn("file", res.data["errors"])

    def test_upload_requires_authentication(self):
        self.assertEqual(self.upload(pdf_file()).status_code, 401)

    def test_recruiter_cannot_upload_or_read_resumes(self):
        self.login_as("recruiter")
        self.assertEqual(self.upload(pdf_file()).status_code, 403)
        self.assertEqual(self.client.get(LIST_URL).status_code, 403)
        self.assertEqual(self.client.get(ME_URL).status_code, 403)
        self.assertEqual(Resume.objects.count(), 0)

    def test_image_only_pdf_is_saved_as_failed(self):
        self.login_as("candidate")
        res = self.upload(SimpleUploadedFile("scan.pdf", make_pdf(text="")))
        self.assertEqual(res.status_code, 201)
        resume = res.data["resume"]
        self.assertEqual(resume["parsing_status"], "failed")
        self.assertIn("No readable text", resume["parsing_error"])
        self.assertFalse(resume["is_active"])
        self.assertEqual(resume["skills"], [])
        self.assertEqual(self.client.get(ME_URL).status_code, 404)  # nothing active

    # ---------- versions ----------
    def test_new_upload_becomes_active_and_old_one_is_kept(self):
        self.login_as("candidate")
        first = self.upload(pdf_file("one.pdf")).data["resume"]["id"]
        second = self.upload(docx_file("two.docx")).data["resume"]["id"]
        self.assertFalse(Resume.objects.get(pk=first).is_active)
        self.assertTrue(Resume.objects.get(pk=second).is_active)
        self.assertEqual(self.client.get(ME_URL).data["id"], second)
        self.assertEqual(self.client.get(LIST_URL).data["count"], 2)

    def test_skills_are_shared_not_duplicated(self):
        self.login_as("candidate")
        self.upload(pdf_file())
        self.upload(pdf_file("again.pdf"))
        self.assertEqual(Skill.objects.filter(name="Python").count(), 1)

    def test_resume_limit_per_candidate(self):
        self.login_as("candidate")
        for i in range(5):
            self.assertEqual(self.upload(pdf_file(f"r{i}.pdf")).status_code, 201)
        res = self.upload(pdf_file("sixth.pdf"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("up to 5", res.data["errors"]["file"][0])
        self.assertEqual(Resume.objects.count(), 5)

    def test_activate_older_resume(self):
        self.login_as("candidate")
        first = self.upload(pdf_file("one.pdf")).data["resume"]["id"]
        self.upload(pdf_file("two.pdf"))
        res = self.client.post(f"/api/resumes/{first}/activate/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.client.get(ME_URL).data["id"], first)
        self.assertEqual(Resume.objects.filter(is_active=True).count(), 1)

    def test_failed_resume_cannot_be_activated(self):
        self.login_as("candidate")
        failed = self.upload(SimpleUploadedFile("scan.pdf", make_pdf(text=""))).data["resume"]["id"]
        self.assertEqual(self.client.post(f"/api/resumes/{failed}/activate/").status_code, 400)

        def test_recruiter_blocked_from_id_based_endpoints(self):
            self.login_as("candidate", "owner@example.com")
            rid = self.upload(pdf_file()).data["resume"]["id"]
            self.login_as("recruiter")
            self.assertEqual(self.client.get(f"/api/resumes/{rid}/").status_code, 403)
            self.assertEqual(self.client.delete(f"/api/resumes/{rid}/").status_code, 403)
            self.assertEqual(self.client.post(f"/api/resumes/{rid}/activate/").status_code, 403)
            self.assertTrue(Resume.objects.filter(pk=rid).exists())

    def test_failed_upload_does_not_change_active_resume(self):
        self.login_as("candidate")
        good = self.upload(pdf_file()).data["resume"]["id"]
        self.upload(SimpleUploadedFile("scan.pdf", make_pdf(text="")))
        self.assertEqual(self.client.get(ME_URL).data["id"], good)
        self.assertEqual(Resume.objects.filter(is_active=True).count(), 1)

    def test_very_large_request_rejected_early(self):
        self.login_as("candidate")
        huge = b"%PDF-" + b"0" * (7 * 1024 * 1024)
        res = self.upload(SimpleUploadedFile("huge.pdf", huge))
        self.assertEqual(res.status_code, 400)
        self.assertIn("too large", res.data["errors"]["file"][0])

    # ---------- reading ----------
    def test_get_me_and_detail(self):
        self.login_as("candidate")
        rid = self.upload(pdf_file()).data["resume"]["id"]
        me = self.client.get(ME_URL)
        self.assertEqual(me.status_code, 200)
        self.assertIn("extracted_text", me.data)
        detail = self.client.get(f"/api/resumes/{rid}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["id"], rid)

    def test_me_is_404_when_no_resume(self):
        self.login_as("candidate")
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, 404)
        self.assertIn("message", res.data)

    def test_candidate_cannot_access_another_candidates_resume(self):
        self.login_as("candidate", "a@example.com")
        a_resume = self.upload(pdf_file()).data["resume"]["id"]
        self.login_as("candidate", "b@example.com")
        self.assertEqual(self.client.get(f"/api/resumes/{a_resume}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/resumes/{a_resume}/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/resumes/{a_resume}/activate/").status_code, 404)
        self.assertEqual(self.client.get(LIST_URL).data["count"], 0)
        self.assertEqual(self.client.get(ME_URL).status_code, 404)
        self.assertTrue(Resume.objects.filter(pk=a_resume).exists())

    def test_unauthenticated_cannot_read(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)
        self.assertEqual(self.client.get(ME_URL).status_code, 401)
        self.assertEqual(self.client.get("/api/resumes/1/").status_code, 401)

    # ---------- deleting ----------
    def test_delete_removes_row_and_file(self):
        self.login_as("candidate")
        rid = self.upload(pdf_file()).data["resume"]["id"]
        self.assertEqual(len(self.media_files()), 1)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.delete(f"/api/resumes/{rid}/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Resume.objects.filter(pk=rid).exists())
        self.assertEqual(self.media_files(), [])

    def test_deleting_active_resume_promotes_previous_one(self):
        self.login_as("candidate")
        first = self.upload(pdf_file("one.pdf")).data["resume"]["id"]
        second = self.upload(pdf_file("two.pdf")).data["resume"]["id"]
        with self.captureOnCommitCallbacks(execute=True):
            self.client.delete(f"/api/resumes/{second}/")
        self.assertEqual(self.client.get(ME_URL).data["id"], first)

    def test_deleting_user_cleans_up_files(self):
        user = self.login_as("candidate")
        self.upload(pdf_file())
        self.upload(docx_file())
        self.assertEqual(len(self.media_files()), 2)
        with self.captureOnCommitCallbacks(execute=True):
            user.delete()
        self.assertEqual(Resume.objects.count(), 0)
        self.assertEqual(self.media_files(), [])
        self.assertFalse(Candidate.objects.exists())