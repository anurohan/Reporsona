from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _register(client: TestClient, email: str):
    response = client.post("/api/auth/register", json={
        "email": email,
        "password": "a sufficiently long password",
        "display_name": email.split("@")[0],
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_authentication_and_resource_isolation():
    with TestClient(app) as client:
        assert client.get("/api/virtual-friends/").status_code == 401
        first = _register(client, "owner-one@example.com")
        client.headers.update({"Authorization": f"Bearer {first['access_token']}"})
        friend = client.post("/api/virtual-friends/", json={"name": "Private One"}).json()

        second = _register(client, "owner-two@example.com")
        client.headers.update({"Authorization": f"Bearer {second['access_token']}"})
        assert client.get(f"/api/virtual-friends/{friend['id']}").status_code == 404
        assert client.get(f"/api/virtual-friends/{friend['id']}/memories").status_code == 404
        assert client.delete(f"/api/virtual-friends/{friend['id']}").status_code == 404


def test_invalid_and_revoked_tokens_are_rejected():
    with TestClient(app) as client:
        auth = _register(client, "token-owner@example.com")
        client.headers.update({"Authorization": f"Bearer {auth['access_token']}tampered"})
        assert client.get("/api/virtual-friends/").status_code == 401
        client.headers.update({"Authorization": f"Bearer {auth['access_token']}"})
        assert client.post("/api/auth/logout").status_code == 204
        assert client.get("/api/virtual-friends/").status_code == 401


def test_password_validation_and_duplicate_email():
    with TestClient(app) as client:
        assert client.post("/api/auth/register", json={"email": "bad", "password": "short"}).status_code == 422
        payload = {"email": "duplicate@example.com", "password": "a sufficiently long password"}
        assert client.post("/api/auth/register", json=payload).status_code == 201
        assert client.post("/api/auth/register", json=payload).status_code == 409
        assert client.post("/api/auth/login", json={"email": payload["email"], "password": "wrong password"}).status_code == 401
