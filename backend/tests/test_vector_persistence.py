from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.services.vector_store import IndexRegistry


def test_faiss_index_persists_reloads_and_deletes(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "vector_db", "faiss")
    monkeypatch.setattr(settings, "vector_dir", str(tmp_path))
    registry = IndexRegistry()
    ids = ["chunk-a", "chunk-b"]
    vectors = [[1.0, 0.0], [0.0, 1.0]]
    first = registry.build("friend-a", ids, vectors, 2)
    assert first.search([1.0, 0.0], 1)[0][0] == "chunk-a"
    assert (tmp_path / "friend-a.faiss").exists()
    assert (tmp_path / "friend-a.json").exists()
    registry.add("friend-a", ["chunk-c"], [[0.7, 0.7]], 2)
    assert registry.get("friend-a").search([0.7, 0.7], 1)[0][0] == "chunk-c"

    restarted = IndexRegistry()
    loaded = restarted.build("friend-a", ids, vectors, 2)
    assert loaded.search([0.0, 1.0], 1)[0][0] == "chunk-b"
    restarted.drop("friend-a")
    assert not (tmp_path / "friend-a.faiss").exists()
    assert not (tmp_path / "friend-a.json").exists()


def test_corrupt_faiss_files_trigger_rebuild(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "vector_db", "faiss")
    monkeypatch.setattr(settings, "vector_dir", str(tmp_path))
    (tmp_path / "friend-b.faiss").write_bytes(b"corrupt")
    (tmp_path / "friend-b.json").write_text("{}", encoding="utf-8")
    registry = IndexRegistry()
    store = registry.build("friend-b", ["chunk"], [[1.0, 0.0]], 2)
    assert store.search([1.0, 0.0], 1)[0][0] == "chunk"
