"""Post-run Slack + email notifications with signed share links."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from aaf.config import get_settings
from app import db as db_mod
from app.models.config import TenantNotificationConfig
from app.models.governance import GovernanceRun
from app.security import decrypt_json
from app.services.share_link import mint_governance_share_token

_log = logging.getLogger(__name__)


def _share_url_for_run(*, run_id: int, tenant_id: int, ttl_seconds: int) -> tuple[str, datetime]:
    settings = get_settings()
    token = mint_governance_share_token(run_id=run_id, tenant_id=tenant_id, ttl_seconds=ttl_seconds)
    base = settings.public_share_base_url.strip().rstrip("/")
    if not base:
        base = "http://localhost:8000"
    path = f"{settings.api_v1_prefix}/public/share/{token}"
    url = f"{base}{path}"
    exp = datetime.fromtimestamp(int(time.time()) + ttl_seconds, tz=timezone.utc)
    return url, exp


def _slack_webhook_url(row: TenantNotificationConfig) -> str | None:
    if not row.slack_incoming_webhook_encrypted:
        return None
    try:
        payload = decrypt_json(row.slack_incoming_webhook_encrypted, secret=get_settings().app_encryption_key)
    except Exception:  # noqa: BLE001
        return None
    u = payload.get("url")
    return str(u).strip() if u else None


def _notify_emails(row: TenantNotificationConfig) -> list[str]:
    raw = row.governance_run_notify_emails_json
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        s = str(item).strip().lower()
        if s and "@" in s:
            out.append(s)
    return out


def deliver_run_complete_notifications(run_id: int) -> None:
    """Best-effort delivery after a successful governance run (own DB session)."""
    db = db_mod.SessionLocal()
    try:
        run = db.get(GovernanceRun, run_id)
        if run is None or run.tenant_id is None:
            return
        row = (
            db.execute(select(TenantNotificationConfig).where(TenantNotificationConfig.tenant_id == run.tenant_id))
            .scalar_one_or_none()
        )
        if row is None or not row.governance_notify_on_run_complete:
            return

        ttl_h = max(1, get_settings().share_link_default_ttl_hours)
        ttl_seconds = ttl_h * 3600
        share_url, _exp = _share_url_for_run(run_id=run.id, tenant_id=run.tenant_id, ttl_seconds=ttl_seconds)

        prompt_preview = (run.prompt or "").strip().replace("\n", " ")
        if len(prompt_preview) > 160:
            prompt_preview = prompt_preview[:159] + "…"

        slack_url = _slack_webhook_url(row)
        if slack_url:
            text = (
                f"*Governance run #{run.id}* completed.\n"
                f"Prompt: {prompt_preview}\n"
                f"Signed share (time-limited): {share_url}"
            )
            try:
                resp = httpx.post(slack_url, json={"text": text}, timeout=10.0)
                if resp.status_code >= 400:
                    _log.warning("slack_webhook_failed", extra={"status": resp.status_code, "run_id": run.id})
            except Exception as exc:  # noqa: BLE001
                _log.warning("slack_webhook_error", extra={"run_id": run.id, "error": str(exc)})

        emails = _notify_emails(row)
        if emails and row.smtp_host and row.smtp_port and row.notifications_enabled:
            from app.services.email_runtime import send_plain_email

            subject = f"Governance run #{run.id} completed"
            body = (
                f"Run #{run.id} finished successfully.\n\n"
                f"Prompt: {prompt_preview}\n\n"
                f"Open the signed snapshot (no login required until expiry):\n{share_url}\n\n"
                f"PDF one-pager: {share_url}/onepager.pdf\n"
            )
            for to in emails:
                try:
                    send_plain_email(row, to_email=to, subject=subject, body=body)
                except Exception as exc:  # noqa: BLE001
                    _log.warning("governance_notify_email_failed", extra={"run_id": run.id, "to": to, "error": str(exc)})
    finally:
        db.close()
