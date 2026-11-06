"""Tests for user-provided source ingestion (text + upload)."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _osho_id(client) -> str:
    personas = client.get("/api/personas").json()
    return next(p["id"] for p in personas if p["slug"] == "osho")


def test_add_text_source_grows_corpus(client):
    pid = _osho_id(client)
    before = client.get(f"/api/personas/{pid}/sources").json()

    r = client.post(
        f"/api/personas/{pid}/sources/text",
        json={
            "title": "User note on silence",
            "text": (
                "Silence is not empty. In stillness the noise of the mind settles "
                "and awareness becomes clear. This is a user-provided passage added "
                "to the corpus for testing ingestion and retrieval."
            ),
            "source_type": "text",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["extraction"] == "text"
    assert body["chunks_added"] >= 1

    after = client.get(f"/api/personas/{pid}/sources").json()
    assert len(after) == len(before) + 1

    # the new material should now be retrievable via chat
    chat = client.post(
        "/api/chat",
        json={"persona_id": pid, "message": "What about silence and stillness?"},
    )
    assert chat.status_code == 200


def test_upload_text_file(client):
    pid = _osho_id(client)
    content = b"Freedom begins the moment you stop waiting for permission to be yourself."
    files = {"file": ("note.txt", io.BytesIO(content), "text/plain")}
    r = client.post(f"/api/personas/{pid}/sources/upload", files=files, data={"title": "Uploaded note"})
    assert r.status_code == 200, r.text
    assert r.json()["extraction"] == "text"
    assert r.json()["chunks_added"] >= 1


def test_unsupported_upload_rejected(client):
    pid = _osho_id(client)
    files = {"file": ("thing.xyz", io.BytesIO(b"data"), "application/octet-stream")}
    r = client.post(f"/api/personas/{pid}/sources/upload", files=files)
    assert r.status_code == 415
