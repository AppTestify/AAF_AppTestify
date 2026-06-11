"""DB-backed auth rate limiter tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "rate_limit.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret-key-min-32-chars!!")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password-123")
    monkeypatch.setenv("RATE_LIMIT_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_MINUTES", "10")
    from app import deps

    deps.settings_dep.cache_clear()
    from app.main import app

    with TestClient(app, base_url="https://testserver") as c:
        yield c
    deps.settings_dep.cache_clear()


def test_rate_limit_blocks_after_max_failures(client: TestClient):
    for _ in range(3):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "wrong"},
        )
        assert r.status_code == 401
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong"},
    )
    assert r.status_code == 429


def test_successful_login_clears_rate_limit(client: TestClient):
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong"},
    )
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    assert r.status_code == 200
    assert "access_token" in r.cookies
