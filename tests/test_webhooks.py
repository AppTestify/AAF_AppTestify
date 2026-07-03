"""Tests for GitHub, Jira, and GitLab webhooks."""

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


def _jira_signature(body: bytes, secret: str) -> str:
    """Compute Jira HMAC SHA256 signature."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _gitlab_token(secret: str) -> str:
    """GitLab webhook token is just the raw secret."""
    return secret


# ============================================================================
# GitHub Webhook Tests
# ============================================================================

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


# ============================================================================
# Jira Webhook Tests
# ============================================================================

def test_jira_webhook_no_signature_when_secret_not_configured(client):
    """Jira webhook without secret configured should accept requests."""
    payload = {"issue": {"key": "PROJ-123"}}
    resp = client.post(
        "/api/v1/webhooks/jira",
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["issue_key"] == "PROJ-123"
    assert data["cache_invalidated_at"] is not None


def test_jira_webhook_rejects_spoofed_signature(client, monkeypatch):
    """Jira webhook with signature should reject mismatched HMAC."""
    secret = "jira-webhook-secret"
    monkeypatch.setenv("JIRA_WEBHOOK_SECRET", secret)
    from app import deps

    deps.settings_dep.cache_clear()
    payload = {"issue": {"key": "PROJ-456"}}
    body = json.dumps(payload).encode()
    wrong_sig = _jira_signature(body, "wrong-secret")
    resp = client.post(
        "/api/v1/webhooks/jira",
        content=body,
        headers={"X-Atlassian-Webhook-Signature": wrong_sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 401
    assert "Invalid webhook signature" in resp.json()["detail"]
    deps.settings_dep.cache_clear()


def test_jira_webhook_rejects_unsigned_when_secret_configured(client, monkeypatch):
    """Jira webhook with secret configured should reject unsigned requests."""
    secret = "jira-webhook-secret"
    monkeypatch.setenv("JIRA_WEBHOOK_SECRET", secret)
    from app import deps

    deps.settings_dep.cache_clear()
    payload = {"issue": {"key": "PROJ-789"}}
    resp = client.post(
        "/api/v1/webhooks/jira",
        json=payload,
    )
    assert resp.status_code == 401
    assert "Missing webhook signature" in resp.json()["detail"]
    deps.settings_dep.cache_clear()


def test_jira_webhook_accepts_valid_signature(client, monkeypatch):
    """Jira webhook with correct HMAC signature should be accepted."""
    secret = "jira-webhook-secret"
    monkeypatch.setenv("JIRA_WEBHOOK_SECRET", secret)
    from app import deps

    deps.settings_dep.cache_clear()
    payload = {"issue": {"key": "PROJ-999"}}
    body = json.dumps(payload).encode()
    sig = _jira_signature(body, secret)
    resp = client.post(
        "/api/v1/webhooks/jira",
        content=body,
        headers={"X-Atlassian-Webhook-Signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["issue_key"] == "PROJ-999"
    assert data["cache_invalidated_at"] is not None
    deps.settings_dep.cache_clear()


def test_jira_webhook_invalidates_cache(client):
    """Jira webhook should invalidate cache for the issue key."""
    payload = {"issue": {"key": "PROJ-111"}}
    resp = client.post(
        "/api/v1/webhooks/jira",
        json=payload,
    )
    assert resp.status_code == 200
    invalidated_at = resp.json()["cache_invalidated_at"]
    assert invalidated_at is not None
    # Verify cache was set
    token = get_ci_cache_token("jira:PROJ-111")
    assert token == invalidated_at


# ============================================================================
# GitLab Webhook Tests
# ============================================================================

def test_gitlab_webhook_no_token_when_secret_not_configured(client):
    """GitLab webhook without secret configured should accept requests."""
    payload = {"project": {"path_with_namespace": "group/project"}}
    resp = client.post(
        "/api/v1/webhooks/gitlab",
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["project"] == "group/project"
    assert data["cache_invalidated_at"] is not None


def test_gitlab_webhook_rejects_spoofed_token(client, monkeypatch):
    """GitLab webhook with token should reject mismatched token."""
    secret = "gitlab-webhook-token"
    monkeypatch.setenv("GITLAB_WEBHOOK_SECRET", secret)
    from app import deps

    deps.settings_dep.cache_clear()
    payload = {"project": {"path_with_namespace": "group/project"}}
    resp = client.post(
        "/api/v1/webhooks/gitlab",
        json=payload,
        headers={"X-Gitlab-Token": "wrong-token"},
    )
    assert resp.status_code == 401
    assert "Invalid webhook token" in resp.json()["detail"]
    deps.settings_dep.cache_clear()


def test_gitlab_webhook_rejects_unsigned_when_secret_configured(client, monkeypatch):
    """GitLab webhook with secret configured should reject unsigned requests."""
    secret = "gitlab-webhook-token"
    monkeypatch.setenv("GITLAB_WEBHOOK_SECRET", secret)
    from app import deps

    deps.settings_dep.cache_clear()
    payload = {"project": {"path_with_namespace": "group/project"}}
    resp = client.post(
        "/api/v1/webhooks/gitlab",
        json=payload,
    )
    assert resp.status_code == 401
    assert "Missing webhook token" in resp.json()["detail"]
    deps.settings_dep.cache_clear()


def test_gitlab_webhook_accepts_valid_token(client, monkeypatch):
    """GitLab webhook with correct token should be accepted."""
    secret = "gitlab-webhook-token"
    monkeypatch.setenv("GITLAB_WEBHOOK_SECRET", secret)
    from app import deps

    deps.settings_dep.cache_clear()
    payload = {"project": {"path_with_namespace": "gitlab-org/gitlab"}}
    resp = client.post(
        "/api/v1/webhooks/gitlab",
        json=payload,
        headers={"X-Gitlab-Token": secret},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["project"] == "gitlab-org/gitlab"
    assert data["cache_invalidated_at"] is not None
    deps.settings_dep.cache_clear()


def test_gitlab_webhook_invalidates_cache(client, monkeypatch):
    """GitLab webhook should invalidate cache for the project."""
    secret = "gitlab-webhook-token"
    monkeypatch.setenv("GITLAB_WEBHOOK_SECRET", secret)
    from app import deps

    deps.settings_dep.cache_clear()
    payload = {"project": {"path_with_namespace": "team/service"}}
    resp = client.post(
        "/api/v1/webhooks/gitlab",
        json=payload,
        headers={"X-Gitlab-Token": secret},
    )
    assert resp.status_code == 200
    invalidated_at = resp.json()["cache_invalidated_at"]
    assert invalidated_at is not None
    # Verify cache was set
    token = get_ci_cache_token("gitlab:team/service")
    assert token == invalidated_at
    deps.settings_dep.cache_clear()


# ============================================================================
# CI Cache Tests
# ============================================================================

def test_ci_cache_invalidate_and_read():
    key = "owner/ci-cache-test"
    ts = invalidate_ci_cache(key)
    assert ts
    assert get_ci_cache_token(key) == ts
