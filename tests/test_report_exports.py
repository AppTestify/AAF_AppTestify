"""Report export and email API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest_auth import cookie_client, login_as


@pytest.fixture
def client(cookie_client):
    return cookie_client


def test_runs_summary_xlsx_and_pdf_export(client: TestClient):
    login_as(client, "admin@example.com", "test-password-123")

    xlsx = client.get("/api/v1/reports/runs/summary?format=xlsx&limit=10")
    assert xlsx.status_code == 200, xlsx.text
    assert xlsx.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(xlsx.content) > 100

    pdf = client.get("/api/v1/reports/runs/summary?format=pdf&limit=10")
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")


def test_audit_events_xlsx_export(client: TestClient):
    login_as(client, "admin@example.com", "test-password-123")
    r = client.get("/api/v1/reports/audit-events?format=xlsx&limit=5")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_report_email_requires_smtp(client: TestClient, monkeypatch):
    login_as(client, "admin@example.com", "test-password-123")

    r = client.post(
        "/api/v1/reports/email",
        json={
            "report_type": "runs_summary",
            "format": "xlsx",
            "recipients": ["ops@example.com"],
            "limit": 5,
        },
    )
    assert r.status_code == 422

    sent: list[dict] = []

    def _fake_send(*args, **kwargs):
        sent.append(kwargs)

    monkeypatch.setattr("app.routers.reports.send_resolved_email_with_attachments", _fake_send)

    save = client.put(
        "/api/v1/tenant/notifications",
        json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "mailer@example.com",
            "smtp_password": "secret-123",
            "smtp_from_email": "no-reply@example.com",
            "use_tls": True,
            "notifications_enabled": True,
            "templates": {},
        },
    )
    assert save.status_code == 200, save.text

    r2 = client.post(
        "/api/v1/reports/email",
        json={
            "report_type": "runs_summary",
            "format": "pdf",
            "recipients": ["ops@example.com"],
            "limit": 5,
        },
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["ok"] is True
    assert sent
    assert sent[0]["attachments"][0][0].endswith(".pdf")
