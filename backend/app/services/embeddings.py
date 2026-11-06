"""Embedding service.

Primary path uses ``sentence-transformers`` (a real multilingual model). When
that dependency is not installed — for example in the zero-dependency Demo Mode
— it transparently falls back to a deterministic hashing/bag-of-words vectoriser
implemented in pure Python. The fallback is not as semantically rich as a neural
model, but it is stable, offline, and good enough to demonstrate lexical
retrieval end to end.

Both paths return L2-normalised ``list[float]`` vectors of length
``settings.embedding_dim`` so downstream cosine similarity is just a dot product.
"""

from __future__ import annotations

import hashlib
import math
import re
import threading
from typing import List

from app.config import settings
from app.services.nlp import STOPWORDS

_WORD_RE = re.compile(r"[\w']+", re.UNICODE)


def _tokenize(text: str) -> List[str]:
    # Drop stopwords and very short tokens so the offline lexical embedder keys
    # on meaningful content words (this markedly improves fallback retrieval).
    return [
        t.lower()
        for t in _WORD_RE.findall(text or "")
        if t.lower() not in STOPWORDS and len(t) > 2
    ]


class EmbeddingService:
    """Lazily-loaded embedding provider with a graceful offline fallback."""

    def __init__(self) -> None:
        self._model = None
        self._backend = None  # None (unloaded) | "sentence-transformers" | "hashing"
        self._lock = threading.Lock()
        self._dim = settings.embedding_dim

    # -- public ----------------------------------------------------------- #
    @property
    def backend(self) -> str:
        self.ensure_loaded()
        return self._backend or "hashing"

    @property
    def dim(self) -> int:
        self.ensure_loaded()
        return self._dim

    def ensure_loaded(self) -> None:
        if self._backend is not None:
            return
        with self._lock:
            if self._backend is not None:
                return
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore

                self._model = SentenceTransformer(settings.embedding_model)
                # method was renamed across versions; support both.
                get_dim = getattr(self._model, "get_embedding_dimension", None) or \
                    self._model.get_sentence_embedding_dimension
                self._dim = int(get_dim())
                self._backend = "sentence-transformers"
            except Exception:
                # No neural model available -> deterministic hashing fallback.
                self._model = None
                self._backend = "hashing"
                self._dim = settings.embedding_dim

    def encode(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        self.ensure_loaded()
        if self._backend == "sentence-transformers" and self._model is not None:
            vecs = self._model.encode(
                texts, normalize_embeddings=True, convert_to_numpy=False
            )
            return [list(map(float, v)) for v in vecs]
        return [self._hash_embed(t) for t in texts]

    def encode_one(self, text: str) -> List[float]:
        return self.encode([text])[0]

    # -- fallback --------------------------------------------------------- #
    def _hash_embed(self, text: str) -> List[float]:
        """Deterministic bag-of-words hashing vectoriser with sublinear TF."""
        dim = self._dim
        vec = [0.0] * dim
        tokens = _tokenize(text)
        if not tokens:
            return vec
        counts: dict[str, int] = {}
        for tok in tokens:
            counts[tok] = counts.get(tok, 0) + 1
        for tok, count in counts.items():
            h = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(h[:4], "little") % dim
            sign = 1.0 if (h[4] & 1) == 0 else -1.0
            weight = 1.0 + math.log(count)
            vec[idx] += sign * weight
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


# Module-level singleton (thread-safe lazy load inside).
embedding_service = EmbeddingService()
