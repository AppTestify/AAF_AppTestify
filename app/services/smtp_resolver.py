"""Resolve effective SMTP settings: tenant override with platform default fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from aaf.config import get_settings
from app.models.config import PlatformNotificationConfig, TenantNotificationConfig
from app.security import decrypt_json


@dataclass(frozen=True)
class ResolvedSmtpConfig:
    source: str  # "tenant" | "platform" | "none"
    smtp_host: str | None
    smtp_port: int | None
    smtp_username: str | None
    smtp_password: str | None
    smtp_from_email: str | None
    smtp_from_name: str | None
    use_tls: bool
    use_ssl: bool
    notifications_enabled: bool
    templates_json: dict[str, Any]

    @property
    def is_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_port and self.notifications_enabled)


def password_from_encrypted(blob: str | None) -> str | None:
    if not blob:
        return None
    payload = decrypt_json(blob, secret=get_settings().app_encryption_key)
    password = payload.get("password")
    return str(password) if password else None


def _tenant_is_complete(row: TenantNotificationConfig) -> bool:
    return bool(row.smtp_host and row.smtp_port and row.notifications_enabled)


def _platform_is_complete(row: PlatformNotificationConfig) -> bool:
    return bool(row.smtp_host and row.smtp_port and row.notifications_enabled)


def get_tenant_notification_config(db: Session, tenant_id: int) -> TenantNotificationConfig | None:
    return (
        db.execute(select(TenantNotificationConfig).where(TenantNotificationConfig.tenant_id == tenant_id))
        .scalar_one_or_none()
    )


def get_platform_notification_config(db: Session) -> PlatformNotificationConfig:
    row = db.execute(select(PlatformNotificationConfig).order_by(PlatformNotificationConfig.id.asc())).scalars().first()
    if row is None:
        row = PlatformNotificationConfig()
        db.add(row)
        db.flush()
    return row


def resolve_smtp_config(
    db: Session,
    tenant_id: int | None,
) -> TenantNotificationConfig | PlatformNotificationConfig | None:
    """Return the ORM SMTP row to use for plain/templated email (tenant override, else platform)."""
    platform = get_platform_notification_config(db)
    tenant_row: TenantNotificationConfig | None = None
    if tenant_id is not None:
        tenant_row = get_tenant_notification_config(db, tenant_id)

    if tenant_row and _tenant_is_complete(tenant_row) and platform.allow_tenant_smtp_override:
        return tenant_row
    if _platform_is_complete(platform):
        return platform
    if tenant_row and tenant_row.smtp_host and tenant_row.smtp_port:
        return tenant_row
    return None


def resolve_smtp_dataclass(db: Session, tenant_id: int | None) -> ResolvedSmtpConfig:
    """Structured SMTP view for HTML templated delivery."""
    row = resolve_smtp_config(db, tenant_id)
    if isinstance(row, TenantNotificationConfig):
        return ResolvedSmtpConfig(
            source="tenant",
            smtp_host=row.smtp_host,
            smtp_port=row.smtp_port,
            smtp_username=row.smtp_username,
            smtp_password=password_from_encrypted(row.smtp_password_encrypted),
            smtp_from_email=row.smtp_from_email or row.smtp_username,
            smtp_from_name=None,
            use_tls=row.use_tls,
            use_ssl=row.use_ssl,
            notifications_enabled=row.notifications_enabled,
            templates_json=row.templates_json if isinstance(row.templates_json, dict) else {},
        )
    if isinstance(row, PlatformNotificationConfig):
        return ResolvedSmtpConfig(
            source="platform",
            smtp_host=row.smtp_host,
            smtp_port=row.smtp_port,
            smtp_username=row.smtp_username,
            smtp_password=password_from_encrypted(row.smtp_password_encrypted),
            smtp_from_email=row.smtp_from_email or row.smtp_username,
            smtp_from_name=row.smtp_from_name,
            use_tls=row.use_tls,
            use_ssl=row.use_ssl,
            notifications_enabled=row.notifications_enabled,
            templates_json=row.templates_json if isinstance(row.templates_json, dict) else {},
        )
    return ResolvedSmtpConfig(
        source="none",
        smtp_host=None,
        smtp_port=None,
        smtp_username=None,
        smtp_password=None,
        smtp_from_email=None,
        smtp_from_name=None,
        use_tls=True,
        use_ssl=False,
        notifications_enabled=False,
        templates_json={},
    )
