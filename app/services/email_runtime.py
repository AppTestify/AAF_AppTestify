"""Tenant/platform SMTP and notification email runtime."""

from __future__ import annotations

from email.message import EmailMessage
import smtplib
from typing import Any

from aaf.config import get_settings
from app.models.config import PlatformNotificationConfig, TenantNotificationConfig
from app.security import decrypt_json
from app.services.smtp_resolver import ResolvedSmtpConfig, resolve_smtp_config

DEFAULT_TEMPLATES: dict[str, dict[str, str]] = {
    "user_welcome": {
        "subject": "Welcome to Casantris",
        "body_text": (
            "Hello {{user_email}},\n\n"
            "Your account has been provisioned for {{tenant_slug}}.\n"
            "Temporary password: {{temporary_password}}\n\n"
            "Please sign in and rotate your password immediately.\n"
            "- Casantris"
        ),
        "body_html": (
            "<p>Hello <strong>{{user_email}}</strong>,</p>"
            "<p>Your account has been provisioned for <em>{{tenant_slug}}</em>.</p>"
            "<p>Temporary password: <code>{{temporary_password}}</code></p>"
            "<p>Please sign in and rotate your password immediately.</p>"
            "<p>— Casantris</p>"
        ),
    },
    "release_hold": {
        "subject": "Release Hold Alert - {{project_key}} {{release_version}}",
        "body_text": "Release decision is HOLD. Risk level: {{risk_level}}. Please review evidence and governance outputs.",
        "body_html": "<p>Release decision is <strong>HOLD</strong> for {{project_key}} {{release_version}}.</p><p>Risk level: {{risk_level}}.</p>",
    },
    "release_go": {
        "subject": "Release Approved - {{project_key}} {{release_version}}",
        "body_text": "Release decision is GO with confidence {{confidence}}. Proceed with controlled rollout.",
        "body_html": "<p>Release <strong>GO</strong> for {{project_key}} {{release_version}} with confidence {{confidence}}.</p>",
    },
    "governance_run_complete": {
        "subject": "Governance run #{{run_id}} completed",
        "body_text": "Run #{{run_id}} finished.\nPrompt: {{prompt_preview}}\nShare link: {{share_url}}",
        "body_html": "<p>Governance run <strong>#{{run_id}}</strong> completed.</p><p>{{prompt_preview}}</p><p><a href='{{share_url}}'>Open snapshot</a></p>",
    },
    "governance_run_failed": {
        "subject": "Governance run #{{run_id}} failed",
        "body_text": "Run #{{run_id}} failed.\nError: {{error_message}}",
        "body_html": "<p>Governance run <strong>#{{run_id}}</strong> failed.</p><p>{{error_message}}</p>",
    },
    "case_created": {
        "subject": "Governance case #{{case_id}} created",
        "body_text": "Case #{{case_id}}: {{case_title}}",
        "body_html": "<p>Governance case <strong>#{{case_id}}</strong> created: {{case_title}}</p>",
    },
    "audit_alert_critical": {
        "subject": "Critical audit alert — {{area}}",
        "body_text": "{{summary}}\nArea: {{area}}\nAction: {{action}}",
        "body_html": "<p><strong>Critical audit alert</strong></p><p>{{summary}}</p><p>Area: {{area}} · Action: {{action}}</p>",
    },
    "report_digest_daily": {
        "subject": "Daily governance digest",
        "body_text": "{{body}}",
        "body_html": "<p><strong>Daily digest</strong></p><p>{{body}}</p>",
    },
    "report_digest_weekly": {
        "subject": "Weekly governance digest",
        "body_text": "{{body}}",
        "body_html": "<p><strong>Weekly digest</strong></p><p>{{body}}</p>",
    },
    "password_reset": {
        "subject": "Password reset for {{user_email}}",
        "body_text": "Use this link to reset your password: {{reset_url}} (expires in {{ttl_minutes}} minutes).",
        "body_html": "<p>Reset your password: <a href='{{reset_url}}'>{{reset_url}}</a> (expires in {{ttl_minutes}} minutes).</p>",
    },
    "access_request_received": {
        "subject": "Access request received — {{organization_name}}",
        "body_text": "We received an access request from {{contact_name}} ({{work_email}}).",
        "body_html": "<p>Access request from <strong>{{contact_name}}</strong> ({{work_email}}) for {{organization_name}}.</p>",
    },
    "case_assigned": {
        "subject": "Case #{{case_id}} assigned to you",
        "body_text": "Governance case #{{case_id}} ({{case_title}}) was assigned. Severity: {{severity}}.",
        "body_html": "<p>Case <strong>#{{case_id}}</strong> assigned: {{case_title}} (severity {{severity}}).</p>",
    },
    "decision_approved": {
        "subject": "Decision approved — case #{{case_id}}",
        "body_text": "Decision {{decision_id}} approved by {{approver_email}}.",
        "body_html": "<p>Decision <strong>{{decision_id}}</strong> approved by {{approver_email}} for case #{{case_id}}.</p>",
    },
    "decision_rejected": {
        "subject": "Decision rejected — case #{{case_id}}",
        "body_text": "Decision {{decision_id}} was rejected. Reason: {{reason}}",
        "body_html": "<p>Decision <strong>{{decision_id}}</strong> rejected for case #{{case_id}}.</p><p>{{reason}}</p>",
    },
    "alert_critical": {
        "subject": "Critical alert — {{alert_title}}",
        "body_text": "Critical alert: {{alert_title}}\n{{alert_summary}}",
        "body_html": "<p><strong>Critical alert:</strong> {{alert_title}}</p><p>{{alert_summary}}</p>",
    },
    "alert_warning": {
        "subject": "Warning — {{alert_title}}",
        "body_text": "Warning: {{alert_title}}\n{{alert_summary}}",
        "body_html": "<p><strong>Warning:</strong> {{alert_title}}</p><p>{{alert_summary}}</p>",
    },
    "audit_digest": {
        "subject": "Audit digest — {{period_label}}",
        "body_text": "Audit digest for {{period_label}}: {{event_count}} events across {{area_count}} areas.",
        "body_html": "<p>Audit digest for <strong>{{period_label}}</strong>: {{event_count}} events, {{area_count}} areas.</p>",
    },
    "onboarding_complete": {
        "subject": "Onboarding complete — {{tenant_slug}}",
        "body_text": "Workspace onboarding is complete for {{tenant_slug}}. You can now run governance workflows.",
        "body_html": "<p>Onboarding complete for <strong>{{tenant_slug}}</strong>. Governance workflows are ready.</p>",
    },
    "integration_failure": {
        "subject": "Integration failure — {{connector_name}}",
        "body_text": "Connector {{connector_name}} validation failed: {{error_message}}",
        "body_html": "<p>Connector <strong>{{connector_name}}</strong> failed: {{error_message}}</p>",
    },
    "governance_run_failed": {
        "subject": "Governance run #{{run_id}} failed",
        "body_text": "Run #{{run_id}} failed.\n\nError: {{error_message}}",
        "body_html": "<p>Governance run <strong>#{{run_id}}</strong> failed.</p><p>{{error_message}}</p>",
    },
    "case_created": {
        "subject": "Governance case #{{case_id}} created",
        "body_text": "New case: {{case_title}}",
        "body_html": "<p>New governance case <strong>#{{case_id}}</strong>: {{case_title}}</p>",
    },
    "report_digest_daily": {
        "subject": "Daily governance digest",
        "body_text": "{{body}}",
        "body_html": "<p>{{body}}</p>",
    },
    "report_digest_weekly": {
        "subject": "Weekly governance digest",
        "body_text": "{{body}}",
        "body_html": "<p>{{body}}</p>",
    },
    "report_on_demand": {
        "subject": "Report attached — {{report_type}}",
        "body_text": "Your requested {{report_type}} report ({{format}}) is attached.",
        "body_html": "<p>Your requested <strong>{{report_type}}</strong> report ({{format}}) is attached.</p>",
    },
}


def _normalize_template(value: dict[str, Any]) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    subject = str(value.get("subject", "")).strip()
    body_text = str(value.get("body_text") or value.get("body") or "").strip()
    body_html = str(value.get("body_html") or body_text.replace("\n", "<br/>")).strip()
    if not subject or not body_text:
        return None
    return {"subject": subject, "body_text": body_text, "body_html": body_html}


def resolved_templates(
    config: TenantNotificationConfig | PlatformNotificationConfig | ResolvedSmtpConfig | None,
) -> dict[str, dict[str, str]]:
    merged = {k: v.copy() for k, v in DEFAULT_TEMPLATES.items()}
    overrides: dict[str, Any] = {}
    if isinstance(config, ResolvedSmtpConfig):
        overrides = config.templates_json
    elif config and isinstance(config.templates_json, dict):
        overrides = config.templates_json
    for key, value in overrides.items():
        normalized = _normalize_template(value if isinstance(value, dict) else {})
        if normalized:
            merged[key] = normalized
    return merged


def _smtp_password(config: TenantNotificationConfig | PlatformNotificationConfig) -> str | None:
    payload = decrypt_json(config.smtp_password_encrypted, secret=get_settings().app_encryption_key)
    password = payload.get("password")
    return str(password) if password else None


def _render(template: str, values: dict[str, Any]) -> str:
    out = template
    for key, value in values.items():
        out = out.replace(f"{{{{{key}}}}}", str(value))
    return out


def _from_header(config: TenantNotificationConfig | PlatformNotificationConfig | ResolvedSmtpConfig) -> str:
    email = config.smtp_from_email or config.smtp_username or "no-reply@casantris.local"
    name = getattr(config, "smtp_from_name", None)
    if name:
        return f"{name} <{email}>"
    return email


def _send_message(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_username: str | None,
    smtp_password: str | None,
    use_tls: bool,
    use_ssl: bool,
    msg: EmailMessage,
) -> None:
    if use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            server.send_message(msg)
        return
    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        if use_tls:
            server.starttls()
        if smtp_username and smtp_password:
            server.login(smtp_username, smtp_password)
        server.send_message(msg)


def test_smtp_connection(config: TenantNotificationConfig | PlatformNotificationConfig) -> None:
    if not config.smtp_host or not config.smtp_port:
        raise ValueError("smtp_host and smtp_port are required")
    if config.use_ssl:
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=8) as server:
            password = _smtp_password(config)
            if config.smtp_username and password:
                server.login(config.smtp_username, password)
    else:
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=8) as server:
            if config.use_tls:
                server.starttls()
            password = _smtp_password(config)
            if config.smtp_username and password:
                server.login(config.smtp_username, password)


def send_html_templated_email(
    smtp: ResolvedSmtpConfig,
    *,
    template_key: str,
    to_email: str,
    values: dict[str, Any],
) -> None:
    if not smtp.is_configured or not smtp.smtp_host or not smtp.smtp_port:
        raise ValueError("SMTP is not configured")
    templates = resolved_templates(smtp)
    template = templates.get(template_key)
    if not template:
        raise ValueError(f"unknown template: {template_key}")
    subject = _render(template["subject"], values)
    body_text = _render(template["body_text"], values)
    body_html = _render(template["body_html"], values)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _from_header(smtp)
    msg["To"] = to_email
    msg.set_content(body_text)
    msg.add_alternative(body_html, subtype="html")
    _send_message(
        smtp_host=smtp.smtp_host,
        smtp_port=smtp.smtp_port,
        smtp_username=smtp.smtp_username,
        smtp_password=smtp.smtp_password,
        use_tls=smtp.use_tls,
        use_ssl=smtp.use_ssl,
        msg=msg,
    )


def send_templated_email(
    config: TenantNotificationConfig,
    *,
    template_key: str,
    to_email: str,
    values: dict[str, Any],
) -> None:
    templates = resolved_templates(config)
    template = templates.get(template_key)
    if not template:
        raise ValueError(f"unknown template: {template_key}")
    subject = _render(template["subject"], values)
    body_text = _render(template["body_text"], values)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _from_header(config)
    msg["To"] = to_email
    msg.set_content(body_text)

    if config.use_ssl:
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=10) as server:
            password = _smtp_password(config)
            if config.smtp_username and password:
                server.login(config.smtp_username, password)
            server.send_message(msg)
        return
    with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=10) as server:
        if config.use_tls:
            server.starttls()
        password = _smtp_password(config)
        if config.smtp_username and password:
            server.login(config.smtp_username, password)
        server.send_message(msg)


def send_plain_email(
    config: TenantNotificationConfig,
    *,
    to_email: str,
    subject: str,
    body: str,
) -> None:
    """Send a simple text email using tenant SMTP (same transport as templated mail)."""
    if not config.smtp_host or not config.smtp_port:
        raise ValueError("smtp_host and smtp_port are required")
    msg = EmailMessage()
    msg["Subject"] = subject.strip() or "(no subject)"
    msg["From"] = _from_header(config)
    msg["To"] = to_email.strip()
    msg.set_content(body)

    if config.use_ssl:
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=10) as server:
            password = _smtp_password(config)
            if config.smtp_username and password:
                server.login(config.smtp_username, password)
            server.send_message(msg)
        return
    with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=10) as server:
        if config.use_tls:
            server.starttls()
        password = _smtp_password(config)
        if config.smtp_username and password:
            server.login(config.smtp_username, password)
        server.send_message(msg)


def send_resolved_plain_email(
    smtp: ResolvedSmtpConfig,
    *,
    to_email: str,
    subject: str,
    body: str,
) -> None:
    if not smtp.is_configured or not smtp.smtp_host or not smtp.smtp_port:
        raise ValueError("SMTP is not configured")
    msg = EmailMessage()
    msg["Subject"] = subject.strip() or "(no subject)"
    msg["From"] = _from_header(smtp)
    msg["To"] = to_email.strip()
    msg.set_content(body)
    _send_message(
        smtp_host=smtp.smtp_host,
        smtp_port=smtp.smtp_port,
        smtp_username=smtp.smtp_username,
        smtp_password=smtp.smtp_password,
        use_tls=smtp.use_tls,
        use_ssl=smtp.use_ssl,
        msg=msg,
    )


def send_resolved_email_with_attachments(
    smtp: ResolvedSmtpConfig,
    *,
    to_emails: list[str],
    subject: str,
    body: str,
    attachments: list[tuple[str, bytes, str]],
    template_key: str | None = None,
    template_values: dict[str, Any] | None = None,
) -> None:
    if not smtp.is_configured or not smtp.smtp_host or not smtp.smtp_port:
        raise ValueError("SMTP is not configured")
    recipients = [e.strip() for e in to_emails if e.strip()]
    if not recipients:
        raise ValueError("at least one recipient is required")

    if template_key:
        templates = resolved_templates(smtp)
        template = templates.get(template_key)
        if template:
            subject = _render(template["subject"], template_values or {})
            body = _render(template["body_text"], template_values or {})

    for to in recipients:
        msg = EmailMessage()
        msg["Subject"] = subject.strip() or "(no subject)"
        msg["From"] = _from_header(smtp)
        msg["To"] = to
        msg.set_content(body)
        for filename, content, mime in attachments:
            maintype, _, subtype = mime.partition("/")
            msg.add_attachment(
                content,
                maintype=maintype or "application",
                subtype=subtype or "octet-stream",
                filename=filename,
            )
        _send_message(
            smtp_host=smtp.smtp_host,
            smtp_port=smtp.smtp_port,
            smtp_username=smtp.smtp_username,
            smtp_password=smtp.smtp_password,
            use_tls=smtp.use_tls,
            use_ssl=smtp.use_ssl,
            msg=msg,
        )
