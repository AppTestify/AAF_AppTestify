"""Unified notification delivery across email, Slack, and Teams."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from aaf.config import get_settings
from app import db as db_mod
from app.models.config import PlatformNotificationConfig, TenantNotificationConfig
from app.models.governance import AuditEvent, GovernanceCase, GovernanceRun
from app.security import decrypt_json
from app.services.email_runtime import send_html_templated_email, send_resolved_plain_email
from app.services.share_link import mint_governance_share_token
from app.services.slack_notifier import send_slack_message
from app.services.smtp_resolver import resolve_smtp_dataclass
from app.services.teams_notifier import send_teams_message

_log = logging.getLogger(__name__)

DEFAULT_CHANNELS: dict[str, dict[str, bool]] = {
    "governance_run_complete": {"email": True, "slack": True, "teams": True},
    "governance_run_failed": {"email": True, "slack": True, "teams": False},
    "case_created": {"email": True, "slack": False, "teams": False},
    "audit_alert_critical": {"email": True, "slack": True, "teams": True},
    "report_digest": {"email": True, "slack": False, "teams": False},
}


def _decrypt_webhook_url(encrypted: str | None) -> str | None:
    if not encrypted:
        return None
    try:
        payload = decrypt_json(encrypted, secret=get_settings().app_encryption_key)
    except Exception:  # noqa: BLE001
        return None
    u = payload.get("url")
    return str(u).strip() if u else None


def _get_tenant_row(db, tenant_id: int) -> TenantNotificationConfig | None:
    return (
        db.execute(select(TenantNotificationConfig).where(TenantNotificationConfig.tenant_id == tenant_id))
        .scalar_one_or_none()
    )


def _get_platform_row(db) -> PlatformNotificationConfig:
    row = db.execute(select(PlatformNotificationConfig).order_by(PlatformNotificationConfig.id.asc())).scalars().first()
    if row is None:
        row = PlatformNotificationConfig(templates_json={})
        db.add(row)
        db.flush()
    return row


def _resolved_channels(row: TenantNotificationConfig | None, event_type: str) -> dict[str, bool]:
    defaults = DEFAULT_CHANNELS.get(event_type, {"email": True, "slack": False, "teams": False})
    raw = row.notification_channels_json if row and isinstance(row.notification_channels_json, dict) else {}
    event_cfg = raw.get(event_type) if isinstance(raw.get(event_type), dict) else {}
    out = defaults.copy()
    for ch in ("email", "slack", "teams"):
        if ch in event_cfg:
            out[ch] = bool(event_cfg[ch])
    return out


def _notify_emails(row: TenantNotificationConfig | None) -> list[str]:
    if row is None:
        return []
    raw = row.governance_run_notify_emails_json
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        s = str(item).strip().lower()
        if s and "@" in s:
            out.append(s)
    return out


def _digest_recipients(row: TenantNotificationConfig | None) -> list[str]:
    if row is None or not isinstance(row.digest_schedule_json, dict):
        return []
    raw = row.digest_schedule_json.get("recipients")
    if not isinstance(raw, list):
        return []
    return [str(x).strip().lower() for x in raw if str(x).strip() and "@" in str(x)]


def _webhook_urls(
    tenant: TenantNotificationConfig | None,
    platform: PlatformNotificationConfig,
) -> tuple[str | None, str | None]:
    slack = _decrypt_webhook_url(tenant.slack_incoming_webhook_encrypted if tenant else None)
    if not slack:
        slack = _decrypt_webhook_url(platform.slack_incoming_webhook_encrypted)
    teams = _decrypt_webhook_url(tenant.teams_incoming_webhook_encrypted if tenant else None)
    if not teams:
        teams = _decrypt_webhook_url(platform.teams_incoming_webhook_encrypted)
    return slack, teams


def _share_url_for_run(*, run_id: int, tenant_id: int, ttl_seconds: int) -> str:
    from app.services.share_link import build_public_share_url

    token = mint_governance_share_token(run_id=run_id, tenant_id=tenant_id, ttl_seconds=ttl_seconds)
    return build_public_share_url(token)


def notify_event(
    db,
    *,
    tenant_id: int,
    event_type: str,
    title: str,
    body: str,
    fields: list[tuple[str, str]] | None = None,
    action_url: str | None = None,
    extra_emails: list[str] | None = None,
    template_key: str | None = None,
    template_values: dict[str, Any] | None = None,
    include_digest_recipients: bool = False,
) -> None:
    tenant = _get_tenant_row(db, tenant_id)
    platform = _get_platform_row(db)
    channels = _resolved_channels(tenant, event_type)

    if event_type == "governance_run_complete" and tenant and not tenant.governance_notify_on_run_complete:
        return

    slack_url, teams_url = _webhook_urls(tenant, platform)
    if channels.get("slack") and slack_url:
        send_slack_message(slack_url, title=title, body=body, fields=fields, action_url=action_url)
    if channels.get("teams") and teams_url:
        send_teams_message(teams_url, title=title, body=body, fields=fields, action_url=action_url)

    if not channels.get("email"):
        return

    smtp = resolve_smtp_dataclass(db, tenant_id)
    if not smtp.is_configured:
        return

    digest = _digest_recipients(tenant) if include_digest_recipients else []
    emails = list(dict.fromkeys(_notify_emails(tenant) + digest + (extra_emails or [])))
    if not emails:
        return

    for to in emails:
        try:
            if template_key:
                send_html_templated_email(
                    smtp,
                    template_key=template_key,
                    to_email=to,
                    values=template_values or {},
                )
            else:
                text = f"{body}\n\n{action_url}" if action_url else body
                send_resolved_plain_email(smtp, to_email=to, subject=title, body=text)
        except Exception as exc:  # noqa: BLE001
            _log.warning("notify_email_failed", extra={"event_type": event_type, "to": to, "error": str(exc)})


def deliver_run_complete(run_id: int) -> None:
    db = db_mod.SessionLocal()
    try:
        run = db.get(GovernanceRun, run_id)
        if run is None or run.tenant_id is None:
            return
        ttl_h = max(1, get_settings().share_link_default_ttl_hours)
        share_url = _share_url_for_run(run_id=run.id, tenant_id=run.tenant_id, ttl_seconds=ttl_h * 3600)
        prompt_preview = (run.prompt or "").strip().replace("\n", " ")
        if len(prompt_preview) > 160:
            prompt_preview = prompt_preview[:159] + "…"
        notify_event(
            db,
            tenant_id=run.tenant_id,
            event_type="governance_run_complete",
            title=f"Governance run #{run.id} completed",
            body=f"Run #{run.id} finished successfully.\nPrompt: {prompt_preview}",
            fields=[("Run", str(run.id)), ("Status", run.status or "succeeded")],
            action_url=share_url,
            template_key="governance_run_complete",
            template_values={
                "run_id": run.id,
                "prompt_preview": prompt_preview,
                "share_url": share_url,
            },
        )
    finally:
        db.close()


def deliver_run_failed(run_id: int) -> None:
    db = db_mod.SessionLocal()
    try:
        run = db.get(GovernanceRun, run_id)
        if run is None or run.tenant_id is None:
            return
        err = (run.error_message or "unknown error")[:500]
        notify_event(
            db,
            tenant_id=run.tenant_id,
            event_type="governance_run_failed",
            title=f"Governance run #{run.id} failed",
            body=f"Run #{run.id} failed after retries.\nError: {err}",
            fields=[("Run", str(run.id)), ("Error", err)],
            template_key="governance_run_failed",
            template_values={"run_id": run.id, "error_message": err},
        )
    finally:
        db.close()


def deliver_case_created(case_id: int) -> None:
    db = db_mod.SessionLocal()
    try:
        case = db.get(GovernanceCase, case_id)
        if case is None or case.tenant_id is None:
            return
        notify_event(
            db,
            tenant_id=case.tenant_id,
            event_type="case_created",
            title=f"Governance case #{case.id} created",
            body=f"Case: {case.title}",
            fields=[("Case", str(case.id)), ("Status", case.status)],
            template_key="case_created",
            template_values={"case_id": case.id, "case_title": case.title},
        )
    finally:
        db.close()


def deliver_audit_critical(audit_event_id: int) -> None:
    db = db_mod.SessionLocal()
    try:
        event = db.get(AuditEvent, audit_event_id)
        if event is None or event.tenant_id is None:
            return
        if str(event.severity).lower() != "critical":
            return
        notify_event(
            db,
            tenant_id=event.tenant_id,
            event_type="audit_alert_critical",
            title="Critical audit alert",
            body=event.summary,
            fields=[
                ("Area", event.area),
                ("Action", event.action),
                ("Severity", event.severity),
            ],
            template_key="alert_critical",
            template_values={
                "alert_title": f"{event.area} / {event.action}",
                "alert_summary": event.summary,
            },
        )
    finally:
        db.close()


def deliver_report_digest(
    *,
    tenant_id: int,
    cadence: str,
    subject: str,
    body: str,
    recipients: list[str],
) -> None:
    db = db_mod.SessionLocal()
    try:
        template_key = "report_digest_daily" if cadence == "daily" else "report_digest_weekly"
        notify_event(
            db,
            tenant_id=tenant_id,
            event_type="report_digest",
            title=subject,
            body=body,
            extra_emails=recipients,
            template_key=template_key,
            template_values={"body": body, "cadence": cadence},
            include_digest_recipients=False,
        )
    finally:
        db.close()
