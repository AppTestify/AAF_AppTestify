from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "rbac_users.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret-key-min-32-chars!!")
    monkeypatch.setenv("SUPERADMIN_EMAIL", "super@example.com")
    monkeypatch.setenv("SUPERADMIN_PASSWORD", "super-pass-123")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password-123")
    from app import deps

    deps.settings_dep.cache_clear()
    from app.main import app

    with TestClient(app) as c:
        yield c

    deps.settings_dep.cache_clear()
    app.dependency_overrides.clear()


def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_user_create_and_notification_config(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    headers = {"Authorization": f"Bearer {token}"}

    notif = client.get("/api/v1/tenant/notifications", headers=headers)
    assert notif.status_code == 200, notif.text
    assert "templates" in notif.json()

    save = client.put(
        "/api/v1/tenant/notifications",
        headers=headers,
        json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "mailer@example.com",
            "smtp_password": "secret-123",
            "smtp_from_email": "no-reply@example.com",
            "use_tls": True,
            "use_ssl": False,
            "notifications_enabled": True,
            "templates": {
                "user_welcome": {"subject": "Welcome {{user_email}}", "body": "Password {{temporary_password}}"}
            },
        },
    )
    assert save.status_code == 200, save.text
    assert save.json()["notifications_enabled"] is True

    created = client.post(
        "/api/v1/rbac/users",
        headers=headers,
        json={"email": "new.user@example.com", "role_name": "reviewer", "is_active": True},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["email"] == "new.user@example.com"
    assert body["role_name"] == "reviewer"

    listed = client.get("/api/v1/rbac/users", headers=headers)
    assert listed.status_code == 200, listed.text
    assert any(x["email"] == "new.user@example.com" for x in listed.json())
