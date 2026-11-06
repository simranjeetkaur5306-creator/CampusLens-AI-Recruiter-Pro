import io
import zipfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from docx import Document

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from .exceptions import NoTextFoundError, ResumeFileError
from .services.text_cleaning import clean_text
from .services.text_extraction import extract_text
from .validators import validate_resume_file

SAMPLE_LINES = [
    "Simran Kaur",
    "simran@example.com | +91 98765 43210",
    "SKILLS",
    "Python, SQL, Machine Learning",
    "EDUCATION",
    "B.Tech in Artificial Intelligence and Machine Learning, Kurukshetra University, 2027",
]
SAMPLE_TEXT = "\n".join(SAMPLE_LINES)


def make_pdf(text=SAMPLE_TEXT, password=None):
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text, fontsize=10)
    if password:
        data = doc.tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password
        )
    else:
        data = doc.tobytes()
    doc.close()
    return data


def make_docx(paragraphs=(), table_rows=()):
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    if table_rows:
        table = document.add_table(rows=0, cols=len(table_rows[0]))
        for row in table_rows:
            cells = table.add_row().cells
            for cell, value in zip(cells, row):
                cell.text = value
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def upload(name, data):
    return SimpleUploadedFile(name, data)


class ValidationTests(SimpleTestCase):
    def test_valid_pdf_accepted(self):
        file_type, data = validate_resume_file(upload("resume.pdf", make_pdf()))
        self.assertEqual(file_type, "pdf")
        self.assertTrue(data.startswith(b"%PDF-"))

    def test_valid_docx_accepted(self):
        file_type, _ = validate_resume_file(upload("resume.DOCX", make_docx(SAMPLE_LINES)))
        self.assertEqual(file_type, "docx")

    def test_unsupported_extension_rejected(self):
        with self.assertRaises(ResumeFileError):
            validate_resume_file(upload("resume.txt", b"hello world"))

    def test_oversized_file_rejected(self):
        big = b"%PDF-" + b"0" * settings.RESUME_MAX_SIZE_BYTES
        with self.assertRaises(ResumeFileError) as ctx:
            validate_resume_file(upload("big.pdf", big))
        self.assertIn("too large", str(ctx.exception))

    def test_empty_file_rejected(self):
        with self.assertRaises(ResumeFileError):
            validate_resume_file(upload("empty.pdf", b""))

    def test_text_file_renamed_to_pdf_rejected(self):
        with self.assertRaises(ResumeFileError):
            validate_resume_file(upload("resume.pdf", b"just plain text, not a pdf"))

    def test_pdf_renamed_to_docx_rejected(self):
        with self.assertRaises(ResumeFileError):
            validate_resume_file(upload("resume.docx", make_pdf()))

    def test_docx_renamed_to_pdf_rejected(self):
        with self.assertRaises(ResumeFileError):
            validate_resume_file(upload("resume.pdf", make_docx(SAMPLE_LINES)))

    def test_corrupted_pdf_rejected(self):
        broken = b"%PDF-1.4\n" + b"this is not a real pdf body " * 50
        with self.assertRaises(ResumeFileError):
            validate_resume_file(upload("broken.pdf", broken))

    def test_corrupted_docx_rejected(self):
        broken = b"PK\x03\x04" + b"garbage" * 20
        with self.assertRaises(ResumeFileError):
            validate_resume_file(upload("broken.docx", broken))

    def test_zip_without_word_document_rejected(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("hello.txt", "hi")
        with self.assertRaises(ResumeFileError):
            validate_resume_file(upload("fake.docx", buffer.getvalue()))

    def test_password_protected_pdf_rejected(self):
        with self.assertRaises(ResumeFileError) as ctx:
            validate_resume_file(upload("locked.pdf", make_pdf(password="secret")))
        self.assertIn("Password-protected", str(ctx.exception))


class ExtractionTests(SimpleTestCase):
    def test_extract_pdf_text(self):
        text = extract_text(make_pdf(), "pdf")
        self.assertIn("Python", text)
        self.assertIn("simran@example.com", text)

    def test_extract_docx_text_including_tables(self):
        data = make_docx(
            SAMPLE_LINES,
            table_rows=[("Languages", "Python, SQL"), ("Frameworks", "Django, React")],
        )
        text = extract_text(data, "docx")
        self.assertIn("Kurukshetra University", text)
        self.assertIn("Python, SQL", text)
        self.assertIn("Django", text)

    def test_blank_pdf_reports_no_text(self):
        with self.assertRaises(NoTextFoundError):
            extract_text(make_pdf(text=""), "pdf")

    def test_empty_docx_reports_no_text(self):
        with self.assertRaises(NoTextFoundError):
            extract_text(make_docx(), "docx")


class CleaningTests(SimpleTestCase):
    def test_clean_text_normalizes(self):
        raw = "\u2022 Built  ML\u00a0model\u200b\n\n\n\n\ufb01nal   result"
        self.assertEqual(clean_text(raw), "- Built ML model\n\nfinal result")