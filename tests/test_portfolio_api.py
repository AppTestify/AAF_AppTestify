from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "portfolio.db"
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


def test_portfolio_project_release_and_executive_report(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    headers = {"Authorization": f"Bearer {token}"}

    project = client.post(
        "/api/v1/portfolio/projects",
        headers=headers,
        json={"key": "CORE", "name": "Core Platform", "owner": "CTO", "status": "active"},
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    release = client.post(
        "/api/v1/portfolio/releases",
        headers=headers,
        json={
            "project_id": project_id,
            "version": "2026.05.1",
            "status": "in_review",
            "release_decision": "go",
            "decision_confidence": 0.82,
            "consensus_score": 0.79,
            "risk_level": "medium",
        },
    )
    assert release.status_code == 201, release.text

    listed_projects = client.get("/api/v1/portfolio/projects", headers=headers)
    assert listed_projects.status_code == 200, listed_projects.text
    assert len(listed_projects.json()) >= 1

    listed_releases = client.get("/api/v1/portfolio/releases", headers=headers)
    assert listed_releases.status_code == 200, listed_releases.text
    assert len(listed_releases.json()) >= 1

    report = client.get("/api/v1/portfolio/reports/executive", headers=headers)
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["projects_total"] >= 1
    assert "project_breakdown" in body

    ops = client.get("/api/v1/portfolio/reports/operations-context", headers=headers)
    assert ops.status_code == 200, ops.text
    ob = ops.json()
    assert "runs_total" in ob
    assert "portfolio_releases_total" in ob
    assert ob["portfolio_releases_total"] >= 1
