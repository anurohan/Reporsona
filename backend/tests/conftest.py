"""Shared pytest fixtures.

Each test run uses an isolated on-disk SQLite database and Demo Mode so no
external services are required.
"""

from __future__ import annotations

import os
import tempfile

import pytest

# Configure environment BEFORE importing app modules (settings is cached).
_TMP_DB = os.path.join(tempfile.gettempdir(), "repersona_test.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("LLM_PROVIDER", "demo")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ.setdefault("VECTOR_DB", "memory")


def authenticate(client, email: str = "audit@example.com", password: str = "correct horse battery staple"):
    response = client.post("/api/auth/register", json={"email": email, "password": password, "display_name": "Audit User"})
    if response.status_code == 409:
        response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code in {200, 201}, response.text
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})
    return response.json()


@pytest.fixture(scope="session")
def db_session():
    from app.database import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="session")
def demo_persona(db_session):
    from app.services.demo_builder import build_ready_persona

    return build_ready_persona(db_session, "Osho", force_demo=True)
