"""Tenant settings / connector / AI provider API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "tenant_cfg.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret-key-min-32-chars!!")
    monkeypatch.setenv("SUPERADMIN_EMAIL", "super@example.com")
    monkeypatch.setenv("SUPERADMIN_PASSWORD", "super-pass-123")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password-123")
    monkeypatch.setenv("SEED_TEST_TENANT", "true")
    monkeypatch.setenv("TEST_TENANT_SLUG", "test")
    monkeypatch.setenv("TEST_TENANT_ADMIN_EMAIL", "testadmin@localhost")
    monkeypatch.setenv("TEST_TENANT_ADMIN_PASSWORD", "changeme")

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


def test_tenant_settings_patch_and_get(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    r0 = client.get("/api/v1/tenant/settings", headers={"Authorization": f"Bearer {token}"})
    assert r0.status_code == 200
    assert r0.json()["tenant_slug"] == "default"

    r1 = client.patch(
        "/api/v1/tenant/settings",
        headers={"Authorization": f"Bearer {token}"},
        json={"default_ai_provider": "openai", "ui_preferences": {"nav_collapsed": True}},
    )
    assert r1.status_code == 200, r1.text
    body = r1.json()
    assert body["default_ai_provider"] == "openai"
    assert body["ui_preferences"]["nav_collapsed"] is True


def test_connector_config_upsert_and_validate(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    r1 = client.put(
        "/api/v1/tenant/connectors",
        headers={"Authorization": f"Bearer {token}"},
        json={"connectors": {"github": {"enabled": True, "config_json": {"repo": "owner/repo"}}}},
    )
    assert r1.status_code == 200, r1.text
    assert any(x["connector_name"] == "github" for x in r1.json())

    r2 = client.post(
        "/api/v1/tenant/connectors/github/validate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["last_validation_ok"] is True

    r3 = client.put(
        "/api/v1/tenant/connectors",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "connectors": {
                "azure": {"enabled": True, "config_json": {"subscription_id": "sub-1"}, "credentials_json": {"client_secret": "x"}},
                "aws": {"enabled": True, "config_json": {"account_id": "123456789012"}, "credentials_json": {"access_key_id": "y"}},
            }
        },
    )
    assert r3.status_code == 200, r3.text
    names = [x["connector_name"] for x in r3.json()]
    assert "azure" in names
    assert "aws" in names


def test_ai_provider_upsert_validate_and_masked_secret(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    r1 = client.put(
        "/api/v1/tenant/ai/providers",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "default_provider": "anthropic",
            "providers": {
                "anthropic": {
                    "enabled": True,
                    "model_name": "claude-sonnet",
                    "api_key_ref": "sk-ant-123456",
                    "temperature": 0.4,
                    "max_tokens": 2048,
                }
            },
        },
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["default_provider"] == "anthropic"
    provider = next(p for p in r1.json()["providers"] if p["provider_name"] == "anthropic")
    assert provider["api_key_ref"].startswith("sk")
    assert "***" in provider["api_key_ref"]

    r2 = client.post(
        "/api/v1/tenant/ai/providers/anthropic/validate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["last_validation_ok"] is True


def test_superadmin_can_target_other_tenant(client: TestClient):
    token = _login(client, "super@example.com", "super-pass-123")
    r1 = client.patch(
        "/api/v1/tenant/settings?tenant_slug=test",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "default_ai_provider": "azure_openai",
            "rag_config_json": {"enabled": True, "documents": ["Runbook A", "Runbook B"]},
            "llm_keys": {"azure_openai": "secret-123"},
        },
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["tenant_slug"] == "test"
    assert r1.json()["default_ai_provider"] == "azure_openai"
    assert r1.json()["rag_config_json"]["enabled"] is True


def test_audit_log_created_on_config_change(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    r = client.patch(
        "/api/v1/tenant/settings",
        headers={"Authorization": f"Bearer {token}"},
        json={"default_ai_provider": "openai"},
    )
    assert r.status_code == 200

    from app import db as db_mod
    from app.models.config import ConfigAuditLog

    db = db_mod.SessionLocal()
    try:
        rows = db.execute(select(ConfigAuditLog)).scalars().all()
        assert len(rows) >= 1
        assert any(x.area == "tenant_settings" and x.action == "update" for x in rows)
    finally:
        db.close()


def test_governance_runtime_uses_tenant_connector_override(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    set_cfg = client.put(
        "/api/v1/tenant/connectors",
        headers={"Authorization": f"Bearer {token}"},
        json={"connectors": {"github": {"enabled": True, "config_json": {"repo": "acme/platform"}}}},
    )
    assert set_cfg.status_code == 200, set_cfg.text

    run = client.post(
        "/api/v1/governance/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Need github status"},
    )
    assert run.status_code == 200, run.text
    runtime = run.json()["runtime_config"]
    assert runtime["connector_mode"].endswith("live")
    assert runtime["github_repo"] == "acme/platform"
