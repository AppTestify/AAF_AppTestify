"""Tenant SMTP and notification email runtime."""

from __future__ import annotations

from email.message import EmailMessage
import smtplib
from typing import Any

from aaf.config import get_settings
from app.models.config import TenantNotificationConfig
from app.security import decrypt_json

DEFAULT_TEMPLATES: dict[str, dict[str, str]] = {
    "user_welcome": {
        "subject": "Welcome to Casantris",
        "body": (
            "Hello {{user_email}},\n\n"
            "Your account has been provisioned for {{tenant_slug}}.\n"
            "Temporary password: {{temporary_password}}\n\n"
            "Please sign in and rotate your password immediately.\n"
            "- Casantris"
        ),
    },
    "release_hold": {
        "subject": "Release Hold Alert - {{project_key}} {{release_version}}",
        "body": "Release decision is HOLD. Risk level: {{risk_level}}. Please review evidence and governance outputs.",
    },
    "release_go": {
        "subject": "Release Approved - {{project_key}} {{release_version}}",
        "body": "Release decision is GO with confidence {{confidence}}. Proceed with controlled rollout.",
    },
}


def resolved_templates(config: TenantNotificationConfig | None) -> dict[str, dict[str, str]]:
    merged = {k: v.copy() for k, v in DEFAULT_TEMPLATES.items()}
    if config and isinstance(config.templates_json, dict):
        for key, value in config.templates_json.items():
            if isinstance(value, dict):
                subject = str(value.get("subject", "")).strip()
                body = str(value.get("body", "")).strip()
                if subject and body:
                    merged[key] = {"subject": subject, "body": body}
    return merged


def _smtp_password(config: TenantNotificationConfig) -> str | None:
    payload = decrypt_json(config.smtp_password_encrypted, secret=get_settings().app_encryption_key)
    password = payload.get("password")
    return str(password) if password else None


def _render(template: str, values: dict[str, Any]) -> str:
    out = template
    for key, value in values.items():
        out = out.replace(f"{{{{{key}}}}}", str(value))
    return out


def test_smtp_connection(config: TenantNotificationConfig) -> None:
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
    body = _render(template["body"], values)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.smtp_from_email or config.smtp_username or "no-reply@casantris.local"
    msg["To"] = to_email
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
    msg["From"] = config.smtp_from_email or config.smtp_username or "no-reply@casantris.local"
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
