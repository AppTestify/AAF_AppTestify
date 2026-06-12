"""Public share snapshot API and SPA URL builder."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.models.governance import GovernanceRun
from app.services.share_link import build_public_share_url, mint_governance_share_token


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "public_share.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret-key-min-32-chars!!")
    monkeypatch.setenv("PUBLIC_SHARE_BASE_URL", "https://app.example.com")
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


def _seed_succeeded_run(*, tenant_id: int, user_id: int) -> int:
    from app.db import SessionLocal

    assert SessionLocal is not None
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        run = GovernanceRun(
            tenant_id=tenant_id,
            requested_by_user_id=user_id,
            prompt="Public share snapshot test",
            status="succeeded",
            finished_at=now,
            result_json={
                "decision_framing": {
                    "orchestration": {
                        "recommended_action": "hold",
                        "consensus_score": 0.72,
                        "utility_score": 0.61,
                        "xi_score": 0.55,
                    }
                },
                "agentic_intelligence": {
                    "incident": {"title": "Release risk elevated"},
                    "executive_summary": {"title": "Hold release", "content": "Consensus below threshold."},
                },
            },
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id


def test_build_public_share_url_uses_frontend_origin(monkeypatch):
    monkeypatch.setenv("PUBLIC_SHARE_BASE_URL", "https://app.casantris.com")
    from app import deps

    deps.settings_dep.cache_clear()
    url = build_public_share_url("abc123")
    assert url == "https://app.casantris.com/share/abc123"
    deps.settings_dep.cache_clear()


def test_public_share_snapshot_json(client: TestClient):
    _login(client)
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200, me.text
    user = me.json()
    run_id = _seed_succeeded_run(tenant_id=int(user["tenant_id"]), user_id=int(user["id"]))

    share = client.post(
        f"/api/v1/governance/runs/{run_id}/share-link",
        json={"expires_in_hours": 24},
    )
    assert share.status_code == 200, share.text
    share_url = share.json()["url"]
    assert share_url.startswith("https://app.example.com/share/")
    share_token = share_url.rsplit("/", 1)[-1]

    snap = client.get(f"/api/v1/public/share/{share_token}/snapshot")
    assert snap.status_code == 200, snap.text
    body = snap.json()
    assert body["run_id"] == run_id
    assert body["recommended_action"] == "hold"
    assert body["pdf_path"].endswith("/onepager.pdf")


def test_share_link_mints_spa_url(client: TestClient, monkeypatch):
    monkeypatch.setenv("PUBLIC_SHARE_BASE_URL", "https://frontend.test")
    from app import deps

    deps.settings_dep.cache_clear()
    token = mint_governance_share_token(run_id=99, tenant_id=1, ttl_seconds=3600)
    assert build_public_share_url(token) == f"https://frontend.test/share/{token}"
    deps.settings_dep.cache_clear()
