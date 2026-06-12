"""Scheduled daily/weekly report digest Celery tasks."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app import db as db_mod
from app.models.config import TenantNotificationConfig
from app.models.tenant import Tenant
from app.services.notification_router import deliver_report_digest

_log = logging.getLogger(__name__)


def _digest_recipients(row: TenantNotificationConfig) -> list[str]:
    raw = row.digest_schedule_json if isinstance(row.digest_schedule_json, dict) else {}
    recipients = raw.get("recipients")
    if not isinstance(recipients, list):
        return []
    return [str(x).strip().lower() for x in recipients if str(x).strip() and "@" in str(x)]


def _should_send(row: TenantNotificationConfig, cadence: str, now: datetime) -> bool:
    schedule = row.digest_schedule_json if isinstance(row.digest_schedule_json, dict) else {}
    if cadence == "daily":
        if not schedule.get("daily_enabled"):
            return False
        target = str(schedule.get("daily_time_utc") or "08:00")
    else:
        if not schedule.get("weekly_enabled"):
            return False
        day = str(schedule.get("weekly_day") or "monday").lower()
        if day != now.strftime("%A").lower():
            return False
        target = str(schedule.get("weekly_time_utc") or "08:00")
    try:
        hour, minute = target.split(":", 1)
        return now.hour == int(hour) and now.minute == int(minute)
    except ValueError:
        return False


def send_scheduled_digests(cadence: str) -> int:
    """Send digest emails for tenants whose schedule matches the current UTC minute."""
    now = datetime.now(timezone.utc)
    db = db_mod.SessionLocal()
    sent = 0
    try:
        rows = db.execute(select(TenantNotificationConfig)).scalars().all()
        for row in rows:
            if not _should_send(row, cadence, now):
                continue
            recipients = _digest_recipients(row)
            if not recipients:
                continue
            tenant = db.get(Tenant, row.tenant_id)
            slug = tenant.slug if tenant else str(row.tenant_id)
            subject = f"{cadence.title()} governance digest — {slug}"
            body = (
                f"Your {cadence} governance digest for tenant '{slug}' is ready.\n"
                "Open Reports in the workspace to download Excel/PDF exports."
            )
            try:
                deliver_report_digest(
                    tenant_id=row.tenant_id,
                    cadence=cadence,
                    subject=subject,
                    body=body,
                    recipients=recipients,
                )
                sent += 1
            except Exception as exc:  # noqa: BLE001
                _log.warning("digest_send_failed", extra={"tenant_id": row.tenant_id, "error": str(exc)})
    finally:
        db.close()
    return sent
