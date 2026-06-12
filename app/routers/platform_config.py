"""Platform-wide configuration (superadmin only)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from aaf.config import get_settings
from app.db import get_db
from app.deps import require_superadmin
from app.models.config import PlatformNotificationConfig
from app.models.user import User
from app.security import encrypt_json
from app.services.email_runtime import resolved_templates, send_html_templated_email, test_smtp_connection
from app.services.smtp_resolver import (
    ResolvedSmtpConfig,
    get_platform_notification_config,
    password_from_encrypted,
)

router = APIRouter(prefix="/platform", tags=["platform-config"])


class PlatformNotificationTemplateOut(BaseModel):
    subject: str
    body_text: str
    body_html: str


class PlatformNotificationConfigOut(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password_configured: bool = False
    smtp_from_email: Optional[str] = None
    smtp_from_name: Optional[str] = None
    use_tls: bool = True
    use_ssl: bool = False
    notifications_enabled: bool = False
    templates: dict[str, PlatformNotificationTemplateOut] = Field(default_factory=dict)
    last_test_ok: Optional[bool] = None
    last_test_error: Optional[str] = None
    last_tested_at: Optional[datetime] = None


class PlatformNotificationTemplateIn(BaseModel):
    subject: str
    body_text: str
    body_html: Optional[str] = None


class PlatformNotificationConfigIn(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_from_name: Optional[str] = None
    use_tls: bool = True
    use_ssl: bool = False
    notifications_enabled: bool = False
    templates: dict[str, PlatformNotificationTemplateIn] = Field(default_factory=dict)


class PlatformNotificationTestIn(BaseModel):
    to_email: Optional[str] = None


def _to_out(row: PlatformNotificationConfig | None) -> PlatformNotificationConfigOut:
    templates = resolved_templates(row)
    return PlatformNotificationConfigOut(
        smtp_host=row.smtp_host if row else None,
        smtp_port=row.smtp_port if row else None,
        smtp_username=row.smtp_username if row else None,
        smtp_password_configured=bool(row and row.smtp_password_encrypted),
        smtp_from_email=row.smtp_from_email if row else None,
        smtp_from_name=row.smtp_from_name if row else None,
        use_tls=row.use_tls if row else True,
        use_ssl=row.use_ssl if row else False,
        notifications_enabled=row.notifications_enabled if row else False,
        templates={
            k: PlatformNotificationTemplateOut(
                subject=v["subject"],
                body_text=v["body_text"],
                body_html=v["body_html"],
            )
            for k, v in templates.items()
        },
        last_test_ok=row.last_test_ok if row else None,
        last_test_error=row.last_test_error if row else None,
        last_tested_at=row.last_tested_at if row else None,
    )


@router.get("/notifications", response_model=PlatformNotificationConfigOut)
def get_platform_notifications(
    db: Session = Depends(get_db),
    current: User = Depends(require_superadmin),
):
    del current
    row = db.execute(select(PlatformNotificationConfig).order_by(PlatformNotificationConfig.id.asc())).scalars().first()
    return _to_out(row)


@router.put("/notifications", response_model=PlatformNotificationConfigOut)
def put_platform_notifications(
    body: PlatformNotificationConfigIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_superadmin),
):
    del current
    row = get_platform_notification_config(db)
    row.smtp_host = body.smtp_host
    row.smtp_port = body.smtp_port
    row.smtp_username = body.smtp_username
    if body.smtp_password:
        row.smtp_password_encrypted = encrypt_json(
            {"password": body.smtp_password},
            secret=get_settings().app_encryption_key,
        )
    row.smtp_from_email = body.smtp_from_email
    row.smtp_from_name = body.smtp_from_name
    row.use_tls = body.use_tls
    row.use_ssl = body.use_ssl
    row.notifications_enabled = body.notifications_enabled
    row.templates_json = {
        k: {
            "subject": v.subject,
            "body_text": v.body_text,
            "body_html": v.body_html or v.body_text.replace("\n", "<br/>"),
        }
        for k, v in body.templates.items()
    }
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.post("/notifications/test")
def test_platform_notifications(
    body: PlatformNotificationTestIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_superadmin),
):
    del current
    row = get_platform_notification_config(db)
    try:
        test_smtp_connection(row)
        if body.to_email:
            smtp = ResolvedSmtpConfig(
                source="platform",
                smtp_host=row.smtp_host,
                smtp_port=row.smtp_port,
                smtp_username=row.smtp_username,
                smtp_password=password_from_encrypted(row.smtp_password_encrypted),
                smtp_from_email=row.smtp_from_email or row.smtp_username,
                smtp_from_name=row.smtp_from_name,
                use_tls=row.use_tls,
                use_ssl=row.use_ssl,
                notifications_enabled=True,
                templates_json=row.templates_json if isinstance(row.templates_json, dict) else {},
            )
            send_html_templated_email(
                smtp,
                template_key="user_welcome",
                to_email=body.to_email,
                values={
                    "user_email": body.to_email,
                    "tenant_slug": "platform",
                    "temporary_password": "test-password",
                },
            )
        row.last_test_ok = True
        row.last_test_error = None
        row.last_tested_at = datetime.now(timezone.utc)
        db.commit()
        return {"ok": True, "message": "Platform SMTP test succeeded"}
    except Exception as exc:  # noqa: BLE001
        row.last_test_ok = False
        row.last_test_error = str(exc)
        row.last_tested_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"SMTP test failed: {exc}") from exc
