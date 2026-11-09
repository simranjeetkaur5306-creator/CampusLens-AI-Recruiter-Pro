import logging
import re
import threading
import unicodedata

import numpy as np
from django.conf import settings

from ..exceptions import EmbeddingError

logger = logging.getLogger(__name__)

_model = None
_fake_model = None
_model_lock = threading.Lock()

_URL_RE = re.compile(r"https?://\S+|www\.\S+|(?:linkedin|github)\.com/\S+", re.I)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")


# ----------------------------------------------------------------------
# Model loading (once per process)
# ----------------------------------------------------------------------
def get_model():
    """Loads the sentence-embedding model on first use and keeps it in memory."""
    global _model, _fake_model
    if getattr(settings, "EMBEDDING_FAKE", False):  # True only while running `manage.py test`
        if _fake_model is None:
            from ..fakes import FakeModel

            _fake_model = FakeModel()
        return _fake_model
    
    if _model is None:
        with _model_lock:
            if _model is None:
                try:
                    from sentence_transformers import SentenceTransformer

                    model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
                except Exception as exc:
                    logger.exception("Could not load the embedding model")
                    raise EmbeddingError(
                        "The embedding model could not be loaded. Check that sentence-transformers "
                        "is installed and that the model can be downloaded."
                    ) from exc
                dimensions = model.get_sentence_embedding_dimension()
                if dimensions != settings.EMBEDDING_DIMENSIONS:
                    raise EmbeddingError(
                        f"The model produces {dimensions}-dimensional vectors but EMBEDDING_DIMENSIONS "
                        f"is {settings.EMBEDDING_DIMENSIONS}. Update the setting (and the database column)."
                    )
                _model = model
    return _model


# ----------------------------------------------------------------------
# Text preparation
# ----------------------------------------------------------------------
def _remove_phone_numbers(text):
    def replace(match):
        digits = sum(ch.isdigit() for ch in match.group(0))
        return " " if digits >= 10 else match.group(0)  # keeps year ranges like "2023 - 2027"

    return _PHONE_RE.sub(replace, text)


def prepare_text(text):
    """Cleans text before embedding.

    Removes links, e-mail addresses and phone numbers (no meaning for matching, and it keeps
    personal contact data out of the vectors), normalizes unicode and whitespace.
    Raises EmbeddingError for missing, non-text or empty input.
    """
    if not isinstance(text, str):
        raise EmbeddingError("Text to embed must be a string.")
    text = unicodedata.normalize("NFKC", text)
    text = _URL_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    text = _remove_phone_numbers(text)
    text = re.sub(r"\s+", " ", text).strip()
    if sum(ch.isalnum() for ch in text) < 10:
        raise EmbeddingError("Text is empty or too short to embed.")
    return text


def chunk_text(text, words=None, overlap=None, max_chunks=None):
    """Splits long text into overlapping word chunks.

    The model reads only a limited number of tokens (about 256 for all-MiniLM-L6-v2) and silently
    ignores the rest, so a long resume is embedded piece by piece and the pieces are averaged.
    """
    words = words or settings.EMBEDDING_CHUNK_WORDS
    overlap = settings.EMBEDDING_CHUNK_OVERLAP if overlap is None else overlap
    max_chunks = max_chunks or settings.EMBEDDING_MAX_CHUNKS
    tokens = text.split()
    chunks, start, step = [], 0, max(words - overlap, 1)
    while start < len(tokens) and len(chunks) < max_chunks:
        chunks.append(" ".join(tokens[start:start + words]))
        if start + words >= len(tokens):
            break
        start += step
    return chunks


# ----------------------------------------------------------------------
# Embedding
# ----------------------------------------------------------------------
def _encode(chunks):
    model = get_model()
    try:
        vectors = model.encode(
            chunks,
            batch_size=16,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
    except Exception as exc:
        logger.exception("Embedding generation failed")
        raise EmbeddingError("Embedding generation failed.") from exc
    vectors = np.asarray(vectors, dtype=np.float32)
    if (
        vectors.ndim != 2
        or vectors.shape[0] != len(chunks)
        or vectors.shape[1] != settings.EMBEDDING_DIMENSIONS
        or not np.isfinite(vectors).all()
    ):
        raise EmbeddingError("The embedding model returned an invalid result.")
    return vectors


def embed_text(text):
    """Returns one unit-length embedding (list of floats) for a piece of text of any length."""
    chunks = chunk_text(prepare_text(text))
    vectors = _encode(chunks)
    mean = vectors.mean(axis=0)
    norm = float(np.linalg.norm(mean))
    if norm == 0.0:
        raise EmbeddingError("The embedding model returned an invalid result.")
    return (mean / norm).astype(float).tolist()


def embed_texts(texts):
    return [embed_text(text) for text in texts]


# ----------------------------------------------------------------------
# What exactly gets embedded for a resume / a job
# ----------------------------------------------------------------------
def resume_document(resume):
    """Text representing a Resume: its extracted skills followed by the cleaned resume text."""
    skills = [skill.name for skill in resume.skills.all()]
    parts = []
    if skills:
        parts.append("Skills: " + ", ".join(skills) + ".")
    parts.append(resume.extracted_text or "")
    return "\n".join(parts)


def job_document(job):
    """Text representing a Job: title, required skills, experience, education and description."""
    skills = [skill.name for skill in job.required_skills.all()]
    lines = [f"Job title: {job.job_title}."]
    if skills:
        lines.append("Required skills: " + ", ".join(skills) + ".")
    lines.append(f"Experience required: {job.required_experience} years.")
    if job.required_education:
        lines.append(f"Education: {job.required_education}.")
    lines.append(job.description)
    return "\n".join(lines)