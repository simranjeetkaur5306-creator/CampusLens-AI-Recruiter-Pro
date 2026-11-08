import numpy as np


def _as_vector(values):
    vector = np.asarray(values, dtype=np.float64)
    if vector.ndim != 1 or vector.size == 0:
        raise ValueError("A vector must be a non-empty one-dimensional list of numbers.")
    if not np.isfinite(vector).all():
        raise ValueError("A vector must not contain NaN or infinite values.")
    return vector


def cosine_similarity(a, b):
    """Cosine similarity of two vectors: dot(a, b) / (|a| * |b|), a value from -1 to 1."""
    va, vb = _as_vector(a), _as_vector(b)
    if va.shape != vb.shape:
        raise ValueError("Vectors must have the same length.")
    norm_a, norm_b = np.linalg.norm(va), np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        raise ValueError("Cannot compare a zero vector.")
    return float(np.clip(np.dot(va, vb) / (norm_a * norm_b), -1.0, 1.0))


def similarity_to_score(similarity):
    """Matching score in percent: the cosine similarity as a percentage, never below 0.

    This is the raw similarity, NOT a calibrated probability of a good hire: with typical
    sentence-embedding models even good matches rarely reach 90 %.
    """
    return round(max(0.0, min(1.0, float(similarity))) * 100, 1)


def rank_vectors(query, items):
    """Ranks {id: vector} by similarity to the query, best first.

    Returns [(id, similarity, score), ...]. Phase 8 does this search inside PostgreSQL
    (pgvector); this pure-Python version is the reference used to check the database results.
    """
    ranked = []
    for item_id, vector in items.items():
        similarity = cosine_similarity(query, vector)
        ranked.append((item_id, similarity, similarity_to_score(similarity)))
    ranked.sort(key=lambda row: row[1], reverse=True)
    return ranked