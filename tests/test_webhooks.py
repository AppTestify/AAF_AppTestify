"""Tests for GitHub workflow_run webhook."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.webhooks import get_ci_cache_token, invalidate_ci_cache


@pytest.fixture
def client():
    return TestClient(app)


def _signed_headers(body: bytes, secret: str) -> dict[str, str]:
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return {"X-GitHub-Event": "workflow_run", "X-Hub-Signature-256": sig}


def test_github_workflow_run_webhook(client):
    payload = {
        "repository": {"full_name": "owner/repo"},
        "workflow_run": {"id": 12345, "conclusion": "failure"},
    }
    resp = client.post(
        "/api/v1/webhooks/github/workflow_run",
        json=payload,
        headers={"X-GitHub-Event": "workflow_run"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["repo"] == "owner/repo"
    assert data["cache_invalidated_at"] is not None


def test_github_webhook_rejects_spoofed_signature(client, monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "unit-test-webhook-secret")
    from app import deps

    deps.settings_dep.cache_clear()
    payload = {"repository": {"full_name": "owner/repo"}, "workflow_run": {"id": 1}}
    body = json.dumps(payload).encode()
    headers = _signed_headers(body, "wrong-secret")
    resp = client.post(
        "/api/v1/webhooks/github/workflow_run",
        content=body,
        headers={**headers, "Content-Type": "application/json"},
    )
    assert resp.status_code == 401
    deps.settings_dep.cache_clear()


def test_github_webhook_rejects_unsigned_when_secret_configured(client, monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "unit-test-webhook-secret")
    from app import deps

    deps.settings_dep.cache_clear()
    payload = {"repository": {"full_name": "owner/repo"}, "workflow_run": {"id": 1}}
    resp = client.post(
        "/api/v1/webhooks/github/workflow_run",
        json=payload,
        headers={"X-GitHub-Event": "workflow_run"},
    )
    assert resp.status_code == 401
    deps.settings_dep.cache_clear()


def test_github_webhook_accepts_valid_signature(client, monkeypatch):
    secret = "unit-test-webhook-secret"
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)
    from app import deps

    deps.settings_dep.cache_clear()
    payload = {"repository": {"full_name": "owner/repo"}, "workflow_run": {"id": 99}}
    body = json.dumps(payload).encode()
    resp = client.post(
        "/api/v1/webhooks/github/workflow_run",
        content=body,
        headers={**_signed_headers(body, secret), "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json()["workflow_run_id"] == 99
    deps.settings_dep.cache_clear()


def test_ci_cache_invalidate_and_read():
    key = "owner/ci-cache-test"
    ts = invalidate_ci_cache(key)
    assert ts
    assert get_ci_cache_token(key) == ts
