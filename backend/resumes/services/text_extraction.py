import io
import logging

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from ..exceptions import NoTextFoundError, ResumeParseError
from .text_cleaning import clean_text, has_enough_text

logger = logging.getLogger(__name__)
MAX_PDF_PAGES = 20  # a resume is never longer; also keeps parsing fast


def extract_text(data, file_type):
    """Returns clean text from PDF/DOCX bytes, or raises ResumeParseError."""
    try:
        raw = _pdf_text(data) if file_type == "pdf" else _docx_text(data)
    except Exception as exc:
        logger.exception("Resume text extraction failed")
        raise ResumeParseError("Could not read text from this file.") from exc

    text = clean_text(raw)
    if not has_enough_text(text):
        raise NoTextFoundError(
            "No readable text found. The resume may be a scanned image; "
            "image-only resumes are not supported yet (OCR is future scope)."
        )
    return text


def _pdf_text(data):
    pages = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for index, page in enumerate(doc):
            if index >= MAX_PDF_PAGES:
                break
            pages.append(page.get_text("text", sort=True))  # sort = natural reading order
    return "\n\n".join(pages)


def _docx_text(data):
    document = Document(io.BytesIO(data))
    lines = []

    # contact details are often placed in the page header
    seen_headers = set()
    for section in document.sections:
        for paragraph in section.header.paragraphs:
            text = paragraph.text.strip()
            if text and text not in seen_headers:
                seen_headers.add(text)
                lines.append(text)

    # paragraphs and tables in their real document order
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            lines.append(Paragraph(child, document).text)
        elif child.tag == qn("w:tbl"):
            for row in Table(child, document).rows:
                cells = []
                for cell in row.cells:
                    text = cell.text.strip().replace("\n", " ")
                    if text and (not cells or cells[-1] != text):  # skip merged-cell repeats
                        cells.append(text)
                if cells:
                    lines.append(" | ".join(cells))
    return "\n".join(lines)