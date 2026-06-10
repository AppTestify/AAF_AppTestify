"""Tests for GitHub workflow_run webhook."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


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
