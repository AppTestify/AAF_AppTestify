"""Shared cookie-auth test helpers."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def cookie_client(monkeypatch, tmp_path):
    db_path = tmp_path / "auth_cookie.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret-key-min-32-chars!!")
    monkeypatch.setenv("SUPERADMIN_EMAIL", "super@example.com")
    monkeypatch.setenv("SUPERADMIN_PASSWORD", "super-pass-123")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password-123")
    from app import deps

    deps.settings_dep.cache_clear()
    from app.main import app

    with TestClient(app, base_url="https://testserver") as c:
        yield c
    deps.settings_dep.cache_clear()
    app.dependency_overrides.clear()


def login_as(client: TestClient, email: str, password: str) -> None:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    assert "access_token" in client.cookies
