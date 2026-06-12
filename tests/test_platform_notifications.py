"""Platform notification config and tenant channel settings tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest_auth import cookie_client, login_as


@pytest.fixture
def client(cookie_client):
    return cookie_client


def test_platform_notifications_superadmin_only(client: TestClient):
    login_as(client, "admin@example.com", "test-password-123")
    denied = client.get("/api/v1/platform/notifications")
    assert denied.status_code == 403

    login_as(client, "super@example.com", "super-pass-123")
    ok = client.get("/api/v1/platform/notifications")
    assert ok.status_code == 200
    assert "templates" in ok.json()


def test_tenant_teams_webhook_and_channel_toggles(client: TestClient):
    login_as(client, "admin@example.com", "test-password-123")

    save = client.put(
        "/api/v1/tenant/notifications",
        json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "notifications_enabled": True,
            "teams_incoming_webhook": "https://outlook.office.com/webhook/example",
            "notification_channels": {
                "governance_run_complete": {"email": True, "slack": True, "teams": True},
            },
            "digest_schedule": {
                "daily_enabled": True,
                "daily_time_utc": "09:00",
                "weekly_enabled": False,
                "weekly_day": "monday",
                "weekly_time_utc": "08:00",
                "recipients": ["digest@example.com"],
            },
            "templates": {},
        },
    )
    assert save.status_code == 200, save.text
    body = save.json()
    assert body["teams_webhook_configured"] is True
    assert body["digest_schedule"]["daily_enabled"] is True
    assert body["digest_schedule"]["recipients"] == ["digest@example.com"]
    assert body["notification_channels"]["governance_run_complete"]["teams"] is True


def test_using_platform_smtp_badge(client: TestClient):
    login_as(client, "super@example.com", "super-pass-123")
    client.put(
        "/api/v1/platform/notifications",
        json={
            "smtp_host": "smtp.platform.example",
            "smtp_port": 587,
            "smtp_from_email": "platform@example.com",
            "notifications_enabled": True,
            "templates": {},
        },
    )

    login_as(client, "admin@example.com", "test-password-123")
    tenant = client.get("/api/v1/tenant/notifications")
    assert tenant.status_code == 200, tenant.text
    assert tenant.json()["using_platform_smtp"] is True
