"""End-to-end API tests via FastAPI TestClient.

The app lifespan seeds a ready 'Osho' demo persona, so chat and graph endpoints
are exercisable without waiting on the async build.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # triggers lifespan (init_db + demo seed)
        yield c


def _osho_id(client) -> str:
    r = client.get("/api/personas")
    assert r.status_code == 200
    personas = r.json()
    osho = next((p for p in personas if p["slug"] == "osho"), None)
    assert osho is not None, "demo persona was not seeded"
    return osho["id"]


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "embedding_backend" in body


def test_ethical_notice(client):
    r = client.get("/api/ethical-notice")
    assert r.status_code == 200
    assert "AI simulation" in r.json()["notice"]


def test_persona_detail_and_graph(client):
    pid = _osho_id(client)
    r = client.get(f"/api/personas/{pid}")
    assert r.status_code == 200
    detail = r.json()
    assert detail["status"] == "ready"
    assert detail["source_count"] >= 4

    g = client.get(f"/api/personas/{pid}/knowledge-graph")
    assert g.status_code == 200
    assert len(g.json()["nodes"]) > 0


def test_chat_flow(client):
    pid = _osho_id(client)
    r = client.post(
        "/api/chat",
        json={"persona_id": pid, "message": "What about fear?", "evidence_mode": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["session_id"]
    assert body["message"].strip()
    assert body["evidence_coverage"] in {"HIGH", "MEDIUM", "LOW"}
    assert body["provider"].startswith("demo")


def test_create_persona_returns_job(client):
    r = client.post("/api/personas/create", json={"name": "Ada Lovelace", "demo": True})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["persona"]["name"] == "Ada Lovelace"
    assert body["job"]["id"]
    assert len(body["job"]["stages"]) == 15
