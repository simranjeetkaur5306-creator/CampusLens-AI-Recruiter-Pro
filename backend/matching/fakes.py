"""Test helper: a fast, deterministic stand-in for the sentence-embedding model.

It hashes words into 384 buckets, so texts that share words get similar vectors. It is NOT
semantic. It only lets the tests check our own code (cleaning, chunking, pooling, validation)
without downloading a real model. Real-model behaviour is checked by `manage.py embedding_demo`.
"""
import hashlib
import re

import numpy as np

DIMENSIONS = 384


class FakeModel:
    def __init__(self):
        self.calls = []  # every list of chunks that was encoded

    def encode(self, sentences, batch_size=32, show_progress_bar=False,
               convert_to_numpy=True, normalize_embeddings=False):
        self.calls.append(list(sentences))
        out = np.zeros((len(sentences), DIMENSIONS), dtype=np.float32)
        for row, sentence in enumerate(sentences):
            for word in re.findall(r"[a-z0-9+#.]+", sentence.lower()):
                out[row, int(hashlib.md5(word.encode()).hexdigest(), 16) % DIMENSIONS] += 1
        if normalize_embeddings:
            norms = np.linalg.norm(out, axis=1, keepdims=True)
            out = out / np.where(norms == 0, 1, norms)
        return out