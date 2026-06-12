"""Actionable automation — decision action execution."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.config import TenantSettings
from app.models.governance import DecisionAction, GovernanceCase


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "action_automation.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret-key-min-32-chars!!")
    monkeypatch.setenv("SUPERADMIN_EMAIL", "super@example.com")
    monkeypatch.setenv("SUPERADMIN_PASSWORD", "super-pass-123")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password-123")
    from app import deps

    deps.settings_dep.cache_clear()
    from app.main import app

    with TestClient(app, base_url="https://testserver") as c:
        yield c
    deps.settings_dep.cache_clear()
    app.dependency_overrides.clear()


def _login(client: TestClient) -> None:
    r = client.post("/api/v1/auth/login", json={"email": "admin@localhost", "password": "test-password-123"})
    assert r.status_code == 200, r.text
    assert "access_token" in client.cookies


def _enable_automation(client: TestClient, *, dry_run: bool = True) -> None:
    r = client.patch(
        "/api/v1/tenant/settings",
        json={
            "ui_preferences": {
                "action_automation": {
                    "enabled": True,
                    "dry_run": dry_run,
                    "jira_blocker_enabled": True,
                    "hold_release_workflow_enabled": True,
                }
            }
        },
    )
    assert r.status_code == 200, r.text


def test_execute_run_actions_hold_release_sim(client: TestClient):
    _login(client)
    _enable_automation(client, dry_run=True)

    run = client.post(
        "/api/v1/governance/runs",
        json={"prompt": "Should we hold release due to CI failures?"},
    )
    assert run.status_code == 202, run.text
    run_id = run.json()["id"]

    import time

    for _ in range(50):
        detail = client.get(f"/api/v1/governance/runs/{run_id}")
        if detail.json().get("status") in {"succeeded", "failed"}:
            break
        time.sleep(0.1)

    # Patch result to hold_release for deterministic test
    from app import db as db_mod
    from app.models.governance import GovernanceRun

    db = db_mod.SessionLocal()
    try:
        row = db.get(GovernanceRun, run_id)
        row.result_json = {
            "orchestration": {"recommended_action": "hold_release", "consensus_score": 0.87},
            "decision_framing": {"orchestration": {"recommended_action": "hold_release", "consensus_score": 0.87}},
        }
        db.commit()
    finally:
        db.close()

    exec_r = client.post(f"/api/v1/governance/runs/{run_id}/execute-actions")
    assert exec_r.status_code == 200, exec_r.text
    actions = exec_r.json()
    assert len(actions) >= 1
    types = {a["action_type"] for a in actions}
    assert "jira_blocker" in types
    assert all(a["state"] in {"simulated", "succeeded"} for a in actions)


def test_approve_decision_triggers_automation(client: TestClient):
    _login(client)
    _enable_automation(client, dry_run=True)

    case_r = client.post(
        "/api/v1/governance/cases",
        json={"title": "Release hold case"},
    )
    assert case_r.status_code == 201, case_r.text
    case_id = case_r.json()["id"]

    dec_r = client.post(
        f"/api/v1/governance/cases/{case_id}/decisions",
        json={"recommended_action": "hold_release", "rationale": "CI red"},
    )
    assert dec_r.status_code == 201, dec_r.text
    decision_id = dec_r.json()["id"]

    approve = client.post(
        f"/api/v1/governance/decisions/{decision_id}/approve",
        json={"final_action": "hold_release", "rationale": "Approved hold"},
    )
    assert approve.status_code == 200, approve.text

    listed = client.get(f"/api/v1/governance/decisions/{decision_id}/actions")
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) >= 1
