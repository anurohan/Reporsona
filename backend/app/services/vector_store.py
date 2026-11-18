"""Vector store abstraction.

A ``VectorStore`` maps embedding vectors -> opaque string ids and supports
top-k cosine search. Two backends are provided:

* ``FaissVectorStore``  — uses faiss + numpy when installed (production path).
* ``MemoryVectorStore`` — pure-Python cosine search, zero dependencies (demo).

The factory picks faiss when available and ``settings.vector_db == "faiss"``,
otherwise falls back to the in-memory store. Swapping in Qdrant/Chroma/Pinecone
later means implementing this same interface — nothing else in the RAG engine
needs to change.

A process-level ``IndexRegistry`` caches one store per persona and lazily
(re)builds it from the persona's chunks, so vectors survive within a running
process without a separate persistence step. For a multi-process/production
deployment, back the registry with a persistent store (Qdrant, pgvector, or a
faiss index written to ``settings.vector_dir``).
"""

from __future__ import annotations

import threading
import json
import os
from pathlib import Path
from abc import ABC, abstractmethod
from typing import List, Sequence, Tuple

from app.config import settings


class VectorStore(ABC):
    def __init__(self, dim: int) -> None:
        self.dim = dim

    @abstractmethod
    def add(self, ids: Sequence[str], vectors: Sequence[Sequence[float]]) -> None: ...

    @abstractmethod
    def search(self, query: Sequence[float], top_k: int) -> List[Tuple[str, float]]: ...

    @abstractmethod
    def __len__(self) -> int: ...


class MemoryVectorStore(VectorStore):
    """Pure-Python cosine search. Vectors are assumed L2-normalised, so cosine
    similarity reduces to a dot product."""

    def __init__(self, dim: int) -> None:
        super().__init__(dim)
        self._ids: List[str] = []
        self._vectors: List[List[float]] = []

    def add(self, ids, vectors) -> None:
        for _id, vec in zip(ids, vectors):
            self._ids.append(_id)
            self._vectors.append(list(map(float, vec)))

    def search(self, query, top_k: int):
        if not self._vectors:
            return []
        q = list(map(float, query))
        scores: List[Tuple[str, float]] = []
        for _id, vec in zip(self._ids, self._vectors):
            s = sum(a * b for a, b in zip(q, vec))
            scores.append((_id, s))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[: max(0, top_k)]

    def __len__(self) -> int:
        return len(self._ids)


class FaissVectorStore(VectorStore):
    """faiss IndexFlatIP (inner product == cosine on normalised vectors)."""

    def __init__(self, dim: int) -> None:
        super().__init__(dim)
        import faiss  # type: ignore
        import numpy as np  # type: ignore

        self._faiss = faiss
        self._np = np
        self._index = faiss.IndexFlatIP(dim)
        self._ids: List[str] = []

    def add(self, ids, vectors) -> None:
        arr = self._np.asarray(vectors, dtype="float32")
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        self._index.add(arr)
        self._ids.extend(list(ids))

    def search(self, query, top_k: int):
        if len(self._ids) == 0:
            return []
        q = self._np.asarray([query], dtype="float32")
        k = min(top_k, len(self._ids))
        scores, idxs = self._index.search(q, k)
        out: List[Tuple[str, float]] = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < 0:
                continue
            out.append((self._ids[int(idx)], float(score)))
        return out

    def __len__(self) -> int:
        return len(self._ids)

    def save(self, index_path: Path, metadata_path: Path) -> None:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        temp_index = index_path.with_suffix(index_path.suffix + ".tmp")
        temp_meta = metadata_path.with_suffix(metadata_path.suffix + ".tmp")
        self._faiss.write_index(self._index, str(temp_index))
        temp_meta.write_text(json.dumps({"version": 1, "dim": self.dim, "ids": self._ids}), encoding="utf-8")
        os.replace(temp_index, index_path)
        os.replace(temp_meta, metadata_path)

    @classmethod
    def load(cls, index_path: Path, metadata_path: Path):
        import faiss  # type: ignore
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        index = faiss.read_index(str(index_path))
        ids = metadata.get("ids", [])
        dim = int(metadata.get("dim", index.d))
        if dim != index.d or len(ids) != index.ntotal:
            raise ValueError("FAISS metadata does not match the index")
        instance = cls.__new__(cls)
        VectorStore.__init__(instance, dim)
        import numpy as np  # type: ignore
        instance._faiss = faiss
        instance._np = np
        instance._index = index
        instance._ids = [str(value) for value in ids]
        return instance


def make_vector_store(dim: int) -> VectorStore:
    if settings.vector_db == "faiss":
        try:
            return FaissVectorStore(dim)
        except Exception:
            pass
    return MemoryVectorStore(dim)


class IndexRegistry:
    """Caches one vector store per persona for the lifetime of the process."""

    def __init__(self) -> None:
        self._stores: dict[str, VectorStore] = {}
        self._lock = threading.Lock()

    def has(self, persona_id: str) -> bool:
        return persona_id in self._stores

    def get(self, persona_id: str) -> VectorStore | None:
        return self._stores.get(persona_id)

    def build(
        self,
        persona_id: str,
        chunk_ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
        dim: int,
    ) -> VectorStore:
        persisted = self._load_if_valid(persona_id, chunk_ids, dim)
        if persisted is not None:
            with self._lock:
                self._stores[persona_id] = persisted
            return persisted
        store = make_vector_store(dim)
        if chunk_ids:
            store.add(chunk_ids, vectors)
        with self._lock:
            self._stores[persona_id] = store
        self._persist(persona_id, store)
        return store

    def _paths(self, persona_id: str) -> tuple[Path, Path]:
        root = Path(settings.vector_dir)
        return root / f"{persona_id}.faiss", root / f"{persona_id}.json"

    def _load_if_valid(self, persona_id: str, chunk_ids: Sequence[str], dim: int) -> VectorStore | None:
        if settings.vector_db != "faiss":
            return None
        index_path, metadata_path = self._paths(persona_id)
        if not index_path.exists() or not metadata_path.exists():
            return None
        try:
            store = FaissVectorStore.load(index_path, metadata_path)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if store.dim != dim or list(metadata.get("ids", [])) != list(chunk_ids):
                return None
            return store
        except Exception:
            return None

    def _persist(self, persona_id: str, store: VectorStore) -> None:
        if settings.vector_db != "faiss" or not isinstance(store, FaissVectorStore):
            return
        index_path, metadata_path = self._paths(persona_id)
        try:
            store.save(index_path, metadata_path)
        except Exception:
            # Retrieval remains available in memory; a later build will retry.
            pass

    def add(
        self,
        persona_id: str,
        chunk_ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
        dim: int,
    ) -> VectorStore:
        """Incrementally append new vectors and atomically update metadata."""
        store = self._stores.get(persona_id)
        if store is None:
            return self.build(persona_id, chunk_ids, vectors, dim)
        store.add(chunk_ids, vectors)
        self._persist(persona_id, store)
        return store

    def drop(self, persona_id: str) -> None:
        with self._lock:
            self._stores.pop(persona_id, None)
        for path in self._paths(persona_id):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


index_registry = IndexRegistry()
