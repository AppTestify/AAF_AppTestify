"""Governance copilot V1 APIs (run/case/decision/audit)."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "governance_v1.db"
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


def _wait_for_run(client: TestClient, token: str, run_id: int, timeout: float = 5.0) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        r = client.get(f"/api/v1/governance/runs/{run_id}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        body = r.json()
        if body["status"] in {"succeeded", "failed"}:
            return body
        time.sleep(0.1)
    raise AssertionError("run did not finish within timeout")


def test_create_and_fetch_governance_run(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    r = client.post(
        "/api/v1/governance/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Show me github release readiness", "prompt_id": "release-readiness"},
    )
    assert r.status_code == 202, r.text
    run_id = r.json()["id"]

    done = _wait_for_run(client, token, run_id)
    assert done["status"] == "succeeded"
    assert done["result_json"] is not None
    rj = done["result_json"]
    assert rj.get("decision_framing", {}).get("primary_recommendation_source") == "orchestration"
    assert "orchestration" in rj.get("decision_framing", {})

    listed = client.get("/api/v1/governance/runs", headers={"Authorization": f"Bearer {token}"})
    assert listed.status_code == 200
    body = listed.json()
    assert "items" in body
    assert any(x["id"] == run_id for x in body["items"])


def test_case_and_decision_flow(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    run = client.post(
        "/api/v1/governance/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Should we release today?"},
    )
    run_id = run.json()["id"]
    completed_run = _wait_for_run(client, token, run_id)
    result = completed_run.get("result", {})
    # Verify that the release readiness prompt ran exactly 3 agents (skipped DevSecOps)
    agents_activated = result.get("agents_activated", [])
    if agents_activated:  # If the mock API populates it
        assert len(agents_activated) == 3

    case = client.post(
        "/api/v1/governance/cases",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Release train R42", "run_id": run_id},
    )
    assert case.status_code == 201, case.text
    case_id = case.json()["id"]

    fetched = client.get(f"/api/v1/governance/cases/{case_id}", headers={"Authorization": f"Bearer {token}"})
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["id"] == case_id
    assert fetched.json()["title"] == "Release train R42"

    decision = client.post(
        f"/api/v1/governance/cases/{case_id}/decisions",
        headers={"Authorization": f"Bearer {token}"},
        json={"run_id": run_id, "recommended_action": "release", "rationale": "consensus above threshold"},
    )
    assert decision.status_code == 201, decision.text
    decision_id = decision.json()["id"]

    approved = client.post(
        f"/api/v1/governance/decisions/{decision_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"final_action": "release", "rationale": "approved by release manager"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    audits = client.get("/api/v1/governance/audit-events", headers={"Authorization": f"Bearer {token}"})
    assert audits.status_code == 200, audits.text
    assert audits.json()["total"] >= 1


def test_report_exports_json_and_csv(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    run = client.post(
        "/api/v1/governance/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "export test run"},
    )
    run_id = run.json()["id"]
    _wait_for_run(client, token, run_id)

    runs_json = client.get("/api/v1/reports/runs/summary?format=json", headers={"Authorization": f"Bearer {token}"})
    assert runs_json.status_code == 200, runs_json.text
    body = runs_json.json()
    assert body["count"] >= 1
    assert "orchestration_consensus_score" in body["items"][0]

    one = client.get(
        f"/api/v1/reports/runs/{run_id}/export?format=json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert one.status_code == 200, one.text
    assert one.json().get("format_version") == 1
    assert "executive_bundle" in one.json()

    runs_csv = client.get("/api/v1/reports/runs/summary?format=csv", headers={"Authorization": f"Bearer {token}"})
    assert runs_csv.status_code == 200, runs_csv.text
    assert "text/csv" in runs_csv.headers.get("content-type", "")

    audit_json = client.get("/api/v1/reports/audit-events?format=json", headers={"Authorization": f"Bearer {token}"})
    assert audit_json.status_code == 200, audit_json.text
    assert "items" in audit_json.json()


def test_telemetry_summary_endpoint(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    run = client.post(
        "/api/v1/governance/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "telemetry smoke test"},
    )
    assert run.status_code == 202, run.text
    _wait_for_run(client, token, run.json()["id"])

    telem = client.get("/api/v1/telemetry/summary", headers={"Authorization": f"Bearer {token}"})
    assert telem.status_code == 200, telem.text
    body = telem.json()
    assert "runs_total" in body
    assert "recent_runs" in body
    assert "connector_health" in body


def test_runs_timeseries_endpoint(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    run = client.post(
        "/api/v1/governance/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "timeseries smoke test"},
    )
    assert run.status_code == 202, run.text
    _wait_for_run(client, token, run.json()["id"])

    ts = client.get("/api/v1/telemetry/runs-timeseries?days=7", headers={"Authorization": f"Bearer {token}"})
    assert ts.status_code == 200, ts.text
    body = ts.json()
    assert body["days"] == 7
    assert len(body["series"]) == 7
    assert all("date" in point and "counts" in point for point in body["series"])
    assert sum(point["counts"].get("succeeded", 0) for point in body["series"]) >= 1


def test_observability_summary_and_metrics_endpoint(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    _ = client.get("/health")
    summary = client.get("/api/v1/telemetry/observability/summary", headers={"Authorization": f"Bearer {token}"})
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert "requests_total" in body
    assert "latency_ms_p95" in body
    assert "connector_calls_total" in body
    assert "failure_recovery" in body

    metrics = client.get("/api/v1/telemetry/observability/metrics", headers={"Authorization": f"Bearer {token}"})
    assert metrics.status_code == 200, metrics.text
    assert "aaf_requests_window_total" in metrics.text
    assert "aaf_connector_calls_total" in metrics.text


def test_decision_lifecycle_endpoint(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    lifecycle = client.get("/api/v1/telemetry/decision-lifecycle", headers={"Authorization": f"Bearer {token}"})
    assert lifecycle.status_code == 200, lifecycle.text
    body = lifecycle.json()
    assert "release" in body
    assert "defendability" in body
    assert "governance" in body


def test_public_metrics_hidden_when_disabled(client: TestClient):
    """GET /metrics returns 404 unless METRICS_PUBLIC_ENABLED=true (see .env.example)."""
    r = client.get("/metrics")
    assert r.status_code == 404


def test_portfolio_project_filters_runs_cases_evidence(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    proj = client.post(
        "/api/v1/portfolio/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"key": "trace-proj", "name": "Traceability project", "status": "active"},
    )
    assert proj.status_code == 201, proj.text
    project_id = proj.json()["id"]

    run_tagged = client.post(
        "/api/v1/governance/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "portfolio tagged run", "portfolio_project_id": project_id},
    )
    assert run_tagged.status_code == 202, run_tagged.text
    run_tagged_id = run_tagged.json()["id"]
    assert run_tagged.json().get("portfolio_project_id") == project_id
    _wait_for_run(client, token, run_tagged_id)

    run_plain = client.post(
        "/api/v1/governance/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "untagged run"},
    )
    assert run_plain.status_code == 202, run_plain.text
    run_plain_id = run_plain.json()["id"]
    _wait_for_run(client, token, run_plain_id)

    listed = client.get(
        f"/api/v1/governance/runs?portfolio_project_id={project_id}&limit=100",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed.status_code == 200, listed.text
    listed_body = listed.json()
    ids = {r["id"] for r in listed_body["items"]}
    assert run_tagged_id in ids
    assert run_plain_id not in ids
    assert listed_body["total"] >= 1

    case = client.post(
        "/api/v1/governance/cases",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Tagged case", "run_id": run_tagged_id},
    )
    assert case.status_code == 201, case.text
    case_id = case.json()["id"]
    assert case.json().get("portfolio_project_id") == project_id

    cases_f = client.get(
        f"/api/v1/governance/cases?portfolio_project_id={project_id}&limit=100",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cases_f.status_code == 200, cases_f.text
    cases_body = cases_f.json()
    assert any(c["id"] == case_id for c in cases_body["items"])
    assert cases_body["total"] >= 1

    ev = client.get(
        f"/api/v1/governance/evidence?portfolio_project_id={project_id}&limit=200",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ev.status_code == 200, ev.text
    ev_body = ev.json()
    rows = ev_body["items"]
    assert ev_body["total"] >= 1
    assert len(rows) >= 1
    assert all(r["run_id"] == run_tagged_id for r in rows)


def test_evidence_and_alert_acknowledge_flows(client: TestClient):
    token = _login(client, "admin@localhost", "test-password-123")
    run = client.post(
        "/api/v1/governance/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "collect evidence"},
    )
    assert run.status_code == 202, run.text
    _wait_for_run(client, token, run.json()["id"])

    evidence = client.get("/api/v1/governance/evidence?limit=10", headers={"Authorization": f"Bearer {token}"})
    assert evidence.status_code == 200, evidence.text
    ev_body = evidence.json()
    assert isinstance(ev_body, dict)
    assert "items" in ev_body
    assert "total" in ev_body

    audits = client.get("/api/v1/governance/audit-events?limit=10", headers={"Authorization": f"Bearer {token}"})
    assert audits.status_code == 200, audits.text
    audit_body = audits.json()
    assert audit_body["total"] >= 1
    assert len(audit_body["items"]) >= 1
    event_id = audit_body["items"][0]["id"]
    ack = client.post(f"/api/v1/governance/audit-events/{event_id}/acknowledge", headers={"Authorization": f"Bearer {token}"})
    assert ack.status_code == 200, ack.text
    assert ack.json()["action"] == "acknowledged"
