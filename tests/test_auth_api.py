"""HTTP auth and protected governance routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "auth_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret-key-min-32-chars!!")
    monkeypatch.setenv("SUPERADMIN_EMAIL", "super@example.com")
    monkeypatch.setenv("SUPERADMIN_PASSWORD", "super-pass-123")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password-123")
    # deps.settings_dep is lru_cached from prior imports; clear so env is picked up
    from app import deps

    deps.settings_dep.cache_clear()

    from app.main import app

    with TestClient(app) as c:
        yield c

    deps.settings_dep.cache_clear()
    app.dependency_overrides.clear()


def test_login_success(client: TestClient):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@example.com"
    assert data["user"]["is_admin"] is True
    assert data["user"]["is_superadmin"] is False
    assert data["user"]["tenant_slug"] == "default"


def test_login_wrong_password(client: TestClient):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong"},
    )
    assert r.status_code == 401


def test_governance_run_requires_auth(client: TestClient):
    r = client.post("/api/v1/governance/run", json={"prompt": "GitHub status"})
    assert r.status_code == 401


def test_governance_run_with_token(client: TestClient):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    token = login.json()["access_token"]
    r = client.post(
        "/api/v1/governance/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "GitHub status"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "consensus" in body
    assert body["consensus"]["consensus_score"] >= 0.0


def test_batch_admin_only(client: TestClient):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    token = login.json()["access_token"]
    r = client.post(
        "/api/v1/governance/batch",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert "runs" in r.json()


def test_superadmin_create_tenant(client: TestClient):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "super@example.com", "password": "super-pass-123"},
    )
    token = login.json()["access_token"]
    r = client.post(
        "/api/v1/admin/tenants",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Acme", "slug": "acme"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["slug"] == "acme"


def test_superadmin_login_and_tenants(client: TestClient):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "super@example.com", "password": "super-pass-123"},
    )
    assert login.status_code == 200, login.text
    data = login.json()
    assert data["user"]["is_superadmin"] is True
    assert data["user"]["tenant_id"] is None
    token = data["access_token"]
    r = client.get("/api/v1/admin/tenants", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    tenants = r.json()
    assert len(tenants) >= 1
    assert any(t["slug"] == "default" for t in tenants)


def test_tenant_admin_cannot_list_tenants(client: TestClient):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    token = login.json()["access_token"]
    r = client.get("/api/v1/admin/tenants", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_superadmin_batch(client: TestClient):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "super@example.com", "password": "super-pass-123"},
    )
    token = login.json()["access_token"]
    r = client.post("/api/v1/governance/batch", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text


def test_me_endpoint(client: TestClient):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    token = login.json()["access_token"]
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "admin@example.com"


def test_signup_status_default_off(client: TestClient):
    r = client.get("/api/v1/auth/signup-status")
    assert r.status_code == 200, r.text
    assert r.json()["tenant_signup_enabled"] is False


def test_signup_tenant_disabled_by_default(client: TestClient):
    r = client.post(
        "/api/v1/auth/signup-tenant",
        json={
            "organization_name": "Acme",
            "tenant_slug": "acme-signup",
            "admin_email": "owner@example.com",
            "password": "password-1234",
        },
    )
    assert r.status_code == 403


def test_signup_tenant_success(client: TestClient, monkeypatch):
    monkeypatch.setenv("PUBLIC_TENANT_SIGNUP_ENABLED", "true")
    from app import deps

    deps.settings_dep.cache_clear()
    r = client.post(
        "/api/v1/auth/signup-tenant",
        json={
            "organization_name": "Planet Express",
            "tenant_slug": "planet-express",
            "admin_email": "ceo@example.org",
            "password": "secure-pass-123",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["user"]["email"] == "ceo@example.org"
    assert data["user"]["tenant_slug"] == "planet-express"
    assert data["user"]["is_admin"] is True
    assert data["user"]["is_superadmin"] is False
    token = data["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["tenant_slug"] == "planet-express"
    deps.settings_dep.cache_clear()


def test_signup_tenant_duplicate_slug(client: TestClient, monkeypatch):
    monkeypatch.setenv("PUBLIC_TENANT_SIGNUP_ENABLED", "true")
    from app import deps

    deps.settings_dep.cache_clear()
    body = {
        "organization_name": "First",
        "tenant_slug": "duplicate-slug",
        "admin_email": "a@example.org",
        "password": "password-1234",
    }
    assert client.post("/api/v1/auth/signup-tenant", json=body).status_code == 201
    r2 = client.post(
        "/api/v1/auth/signup-tenant",
        json={
            **body,
            "organization_name": "Second",
            "admin_email": "b@example.org",
        },
    )
    assert r2.status_code == 409
    deps.settings_dep.cache_clear()
