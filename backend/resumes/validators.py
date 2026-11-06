import io
import os
import zipfile

from django.conf import settings
from docx import Document

try:
    import pymupdf as fitz  # PyMuPDF (new import name)
except ImportError:  # older versions
    import fitz

from .exceptions import ResumeFileError

PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"  # a DOCX file is a ZIP archive
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # protection against zip bombs


def validate_resume_file(uploaded_file):
    """Checks extension, size, real format and corruption.

    Returns (file_type, file_bytes) or raises ResumeFileError.
    """
    name = getattr(uploaded_file, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()
    if ext not in settings.RESUME_ALLOWED_EXTENSIONS:
        raise ResumeFileError("Unsupported file type. Only PDF and DOCX files are allowed.")

    size = uploaded_file.size
    if size == 0:
        raise ResumeFileError("The uploaded file is empty.")
    if size > settings.RESUME_MAX_SIZE_BYTES:
        raise ResumeFileError("File is too large. Maximum allowed size is 5 MB.")

    uploaded_file.seek(0)
    data = uploaded_file.read()
    uploaded_file.seek(0)

    if ext == ".pdf":
        if PDF_MAGIC not in data[:1024]:
            raise ResumeFileError(
                "This file is not a valid PDF (its content does not match the .pdf extension)."
            )
        _check_pdf(data)
        return "pdf", data

    if not data.startswith(ZIP_MAGIC):
        raise ResumeFileError(
            "This file is not a valid DOCX (its content does not match the .docx extension)."
        )
    _check_docx(data)
    return "docx", data


def _check_pdf(data):
    try:
        with fitz.open(stream=data, filetype="pdf") as doc:
            if doc.needs_pass:
                raise ResumeFileError("Password-protected PDFs are not supported.")
            if doc.page_count == 0:
                raise ResumeFileError("The PDF has no pages.")
    except ResumeFileError:
        raise
    except Exception:
        raise ResumeFileError("The PDF is corrupted or cannot be read.")


def _check_docx(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if "word/document.xml" not in archive.namelist():
                raise ResumeFileError("This is not a valid DOCX document.")
            if sum(info.file_size for info in archive.infolist()) > MAX_UNCOMPRESSED_BYTES:
                raise ResumeFileError("The DOCX file expands to an unsafe size.")
            if archive.testzip() is not None:
                raise ResumeFileError("The DOCX file is corrupted.")
        Document(io.BytesIO(data))
    except ResumeFileError:
        raise
    except Exception:
        raise ResumeFileError("The DOCX file is corrupted or cannot be read.")