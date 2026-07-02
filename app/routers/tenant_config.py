"""Tenant-scoped settings, connector, and AI provider configuration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_active_user, require_tenant_admin_or_superadmin
from aaf.config import get_settings
from app.models.config import ConfigAuditLog, PlatformNotificationConfig, TenantAIProviderConfig, TenantConnectorConfig, TenantNotificationConfig, TenantSettings
from app.models.tenant import Tenant
from app.models.user import User
from app.security import decrypt_json, encrypt_json
from app.services.email_runtime import resolved_templates, send_templated_email, test_smtp_connection
from app.services.notification_router import DEFAULT_CHANNELS
from app.services.smtp_resolver import resolve_smtp_dataclass

router = APIRouter(prefix="/tenant", tags=["tenant-config"])

_CONNECTORS = {"github", "gitlab", "jira", "finops", "azure", "aws", "vps", "bitbucket"}
_PROVIDERS = {"openai", "anthropic", "azure_openai", "aws_bedrock", "ollama"}
_SECRET_KEYS = {"token", "api_token", "password", "secret", "key"}


class TenantSettingsOut(BaseModel):
    tenant_slug: str
    default_ai_provider: Optional[str] = None
    ui_preferences: dict[str, Any] = Field(default_factory=dict)
    rag_config_json: dict[str, Any] = Field(default_factory=dict)
    llm_keys_configured: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TenantSettingsPatch(BaseModel):
    default_ai_provider: Optional[str] = None
    ui_preferences: Optional[dict[str, Any]] = None
    rag_config_json: Optional[dict[str, Any]] = None
    llm_keys: Optional[dict[str, str]] = None

    @field_validator("default_ai_provider")
    @classmethod
    def provider_name_ok(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        vv = v.strip().lower()
        if vv and vv not in _PROVIDERS:
            raise ValueError(f"default_ai_provider must be one of: {', '.join(sorted(_PROVIDERS))}")
        return vv or None


class ConnectorConfigIn(BaseModel):
    enabled: bool = False
    config_json: dict[str, Any] = Field(default_factory=dict)
    credentials_json: dict[str, Any] = Field(default_factory=dict)


class ConnectorConfigOut(ConnectorConfigIn):
    connector_name: str
    last_validation_ok: Optional[bool] = None
    last_validation_error: Optional[str] = None
    last_validated_at: Optional[datetime] = None
    telemetry_json: dict[str, Any] = Field(default_factory=dict)
    last_sync_at: Optional[datetime] = None
    credentials_keys_configured: list[str] = Field(default_factory=list)


class ConnectorSetBody(BaseModel):
    connectors: dict[str, ConnectorConfigIn] = Field(default_factory=dict)


class ProviderConfigIn(BaseModel):
    enabled: bool = False
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    endpoint_url: Optional[str] = None
    api_key_ref: Optional[str] = None
    api_key: Optional[str] = None
    timeout_seconds: Optional[int] = None
    retry_count: Optional[int] = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("temperature")
    @classmethod
    def temp_ok(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        if v < 0 or v > 2:
            raise ValueError("temperature must be between 0 and 2")
        return float(v)

    @field_validator("max_tokens", "timeout_seconds", "retry_count")
    @classmethod
    def ints_non_negative(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        if v < 0:
            raise ValueError("value must be >= 0")
        return int(v)


class ProviderConfigOut(ProviderConfigIn):
    provider_name: str
    last_validation_ok: Optional[bool] = None
    last_validation_error: Optional[str] = None
    last_validated_at: Optional[datetime] = None


class ProviderSetBody(BaseModel):
    default_provider: Optional[str] = None
    providers: dict[str, ProviderConfigIn] = Field(default_factory=dict)

    @field_validator("default_provider")
    @classmethod
    def default_provider_ok(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        vv = v.strip().lower()
        if vv and vv not in _PROVIDERS:
            raise ValueError(f"default_provider must be one of: {', '.join(sorted(_PROVIDERS))}")
        return vv or None


class ProviderSetOut(BaseModel):
    default_provider: Optional[str] = None
    providers: list[ProviderConfigOut]


class NotificationTemplateOut(BaseModel):
    subject: str
    body: str


class NotificationChannelToggles(BaseModel):
    email: bool = True
    slack: bool = False
    teams: bool = False


class DigestScheduleOut(BaseModel):
    daily_enabled: bool = False
    daily_time_utc: str = "08:00"
    weekly_enabled: bool = False
    weekly_day: str = "monday"
    weekly_time_utc: str = "08:00"
    recipients: list[str] = Field(default_factory=list)


class NotificationConfigOut(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password_configured: bool = False
    smtp_from_email: Optional[str] = None
    use_tls: bool = True
    use_ssl: bool = False
    notifications_enabled: bool = False
    using_platform_smtp: bool = False
    platform_smtp_configured: bool = False
    slack_webhook_configured: bool = False
    teams_webhook_configured: bool = False
    governance_notify_on_run_complete: bool = False
    governance_run_notify_emails: list[str] = Field(default_factory=list)
    notification_channels: dict[str, NotificationChannelToggles] = Field(default_factory=dict)
    digest_schedule: DigestScheduleOut = Field(default_factory=DigestScheduleOut)
    templates: dict[str, NotificationTemplateOut] = Field(default_factory=dict)
    last_test_ok: Optional[bool] = None
    last_test_error: Optional[str] = None
    last_tested_at: Optional[datetime] = None


class NotificationConfigIn(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    use_tls: bool = True
    use_ssl: bool = False
    notifications_enabled: bool = False
    slack_incoming_webhook: Optional[str] = None
    clear_slack_incoming_webhook: bool = False
    teams_incoming_webhook: Optional[str] = None
    clear_teams_incoming_webhook: bool = False
    governance_notify_on_run_complete: bool = False
    governance_run_notify_emails: list[str] = Field(default_factory=list)
    notification_channels: dict[str, NotificationChannelToggles] = Field(default_factory=dict)
    digest_schedule: Optional[DigestScheduleOut] = None
    templates: dict[str, NotificationTemplateOut] = Field(default_factory=dict)


class NotificationTestIn(BaseModel):
    to_email: Optional[str] = None
    test_slack: bool = False
    slack_webhook: Optional[str] = None


def _resolve_tenant_for_user(
    db: Session,
    user: User,
    tenant_slug: Optional[str],
) -> Tenant:
    if user.is_superadmin:
        if tenant_slug:
            t = db.execute(select(Tenant).where(Tenant.slug == tenant_slug.strip().lower())).scalar_one_or_none()
            if t is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target tenant not found")
            return t
        t_default = db.execute(select(Tenant).order_by(Tenant.slug)).scalars().first()
        if t_default is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No tenants available")
        return t_default

    if user.tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not bound to a tenant")
    t = db.get(Tenant, user.tenant_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return t


def _audit(
    db: Session,
    *,
    tenant_id: int,
    actor_user_id: int,
    area: str,
    action: str,
    target_key: Optional[str],
    before_json: Optional[dict[str, Any]],
    after_json: Optional[dict[str, Any]],
) -> None:
    db.add(
        ConfigAuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            area=area,
            action=action,
            target_key=target_key,
            before_json=before_json,
            after_json=after_json,
        )
    )


def _mask_api_key_ref(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}***{value[-2:]}"


def _sanitize_connector_config(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in payload.items():
        if k.lower() in _SECRET_KEYS:
            out[k] = "***redacted***"
        else:
            out[k] = v
    return out


def _get_or_create_notification_config(db: Session, tenant_id: int) -> TenantNotificationConfig:
    row = db.execute(select(TenantNotificationConfig).where(TenantNotificationConfig.tenant_id == tenant_id)).scalar_one_or_none()
    if row is None:
        row = TenantNotificationConfig(tenant_id=tenant_id, templates_json={})
        db.add(row)
        db.flush()
    return row


@router.get("/settings", response_model=TenantSettingsOut)
def get_tenant_settings(
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    settings = db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)).scalar_one_or_none()
    if settings is None:
        return TenantSettingsOut(
            tenant_slug=tenant.slug,
            default_ai_provider=None,
            ui_preferences={},
            rag_config_json={},
            llm_keys_configured=[],
        )
    llm_keys = decrypt_json(settings.llm_keys_encrypted_json, secret=get_settings().app_encryption_key)
    return TenantSettingsOut(
        tenant_slug=tenant.slug,
        default_ai_provider=settings.default_ai_provider,
        ui_preferences=settings.ui_preferences or {},
        rag_config_json=settings.rag_config_json or {},
        llm_keys_configured=sorted([k for k, v in llm_keys.items() if v]),
    )


@router.patch("/settings", response_model=TenantSettingsOut)
def patch_tenant_settings(
    body: TenantSettingsPatch,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(require_tenant_admin_or_superadmin),
):
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    row = db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)).scalar_one_or_none()
    before = None
    if row is None:
        row = TenantSettings(tenant_id=tenant.id, default_ai_provider=None, ui_preferences={}, rag_config_json={})
        db.add(row)
    else:
        before = {"default_ai_provider": row.default_ai_provider, "ui_preferences": row.ui_preferences}

    payload = body.model_dump(exclude_unset=True)
    if "default_ai_provider" in payload:
        row.default_ai_provider = payload["default_ai_provider"]
    if "ui_preferences" in payload and payload["ui_preferences"] is not None:
        row.ui_preferences = payload["ui_preferences"]
    if "rag_config_json" in payload and payload["rag_config_json"] is not None:
        row.rag_config_json = payload["rag_config_json"]
    if "llm_keys" in payload and payload["llm_keys"] is not None:
        row.llm_keys_encrypted_json = encrypt_json(payload["llm_keys"], secret=get_settings().app_encryption_key)
    db.flush()
    _audit(
        db,
        tenant_id=tenant.id,
        actor_user_id=current.id,
        area="tenant_settings",
        action="update",
        target_key=None,
        before_json=before,
        after_json={"default_ai_provider": row.default_ai_provider, "ui_preferences": row.ui_preferences},
    )
    db.commit()
    return TenantSettingsOut(
        tenant_slug=tenant.slug,
        default_ai_provider=row.default_ai_provider,
        ui_preferences=row.ui_preferences or {},
        rag_config_json=row.rag_config_json or {},
        llm_keys_configured=sorted((payload.get("llm_keys") or {}).keys()) if "llm_keys" in payload else [],
    )


@router.get("/connectors", response_model=list[ConnectorConfigOut])
def get_connector_configs(
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    rows = (
        db.execute(select(TenantConnectorConfig).where(TenantConnectorConfig.tenant_id == tenant.id))
        .scalars()
        .all()
    )
    by_name = {r.connector_name: r for r in rows}
    out: list[ConnectorConfigOut] = []
    encryption_key = get_settings().app_encryption_key
    for name in sorted(_CONNECTORS):
        r = by_name.get(name)
        cred = decrypt_json(r.encrypted_credentials_json, secret=encryption_key) if r and r.encrypted_credentials_json else {}
        out.append(
            ConnectorConfigOut(
                connector_name=name,
                enabled=bool(r.enabled) if r else False,
                config_json=_sanitize_connector_config(r.config_json) if r else {},
                credentials_json={},
                last_validation_ok=r.last_validation_ok if r else None,
                last_validation_error=r.last_validation_error if r else None,
                last_validated_at=r.last_validated_at if r else None,
                telemetry_json=r.telemetry_json if r else {},
                last_sync_at=r.last_sync_at if r else None,
                credentials_keys_configured=sorted([k for k, v in cred.items() if v]),
            )
        )
    return out


@router.put("/connectors", response_model=list[ConnectorConfigOut])
def put_connector_configs(
    body: ConnectorSetBody,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(require_tenant_admin_or_superadmin),
):
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    out: list[ConnectorConfigOut] = []
    encryption_key = get_settings().app_encryption_key
    for name, cfg in body.connectors.items():
        key = name.strip().lower()
        if key not in _CONNECTORS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"connector '{name}' is unsupported",
            )
        row = db.execute(
            select(TenantConnectorConfig).where(
                TenantConnectorConfig.tenant_id == tenant.id, TenantConnectorConfig.connector_name == key
            )
        ).scalar_one_or_none()
        before = None
        if row is None:
            row = TenantConnectorConfig(tenant_id=tenant.id, connector_name=key)
            db.add(row)
        else:
            before = {
                "enabled": row.enabled,
                "config_json": row.config_json,
                "last_validation_ok": row.last_validation_ok,
                "last_validation_error": row.last_validation_error,
            }
        row.enabled = cfg.enabled
        lower_keys = {k.lower() for k in cfg.config_json.keys()}
        if any(k in _SECRET_KEYS for k in lower_keys):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"connector '{key}' config must use secret references, not inline secret keys",
            )
        
        # Clean Jira base URL in config if present
        if key == "jira" and cfg.config_json:
            config_copy = dict(cfg.config_json)
            burl = config_copy.get("base_url")
            if burl and isinstance(burl, str):
                import re
                if "atlassian.net" in burl:
                    match = re.search(r"(https?://[^\/]+\.atlassian\.net)", burl)
                    if match:
                        config_copy["base_url"] = match.group(1)
            row.config_json = config_copy
        else:
            row.config_json = cfg.config_json

        if cfg.credentials_json:
            cleaned_creds = {k: (v.strip() if isinstance(v, str) else v) for k, v in cfg.credentials_json.items()}
            row.encrypted_credentials_json = encrypt_json(cleaned_creds, secret=encryption_key)
        
        row.last_validation_error = None
        row.last_validation_ok = None
        row.last_validated_at = None
        
        cred_keys = []
        if row.encrypted_credentials_json:
            cred_dec = decrypt_json(row.encrypted_credentials_json, secret=encryption_key)
            cred_keys = sorted([k for k, v in cred_dec.items() if v])

        _audit(
            db,
            tenant_id=tenant.id,
            actor_user_id=current.id,
            area="connectors",
            action="upsert",
            target_key=key,
            before_json=before,
            after_json={"enabled": row.enabled, "config_json": row.config_json},
        )
        out.append(
            ConnectorConfigOut(
                connector_name=key,
                enabled=row.enabled,
                config_json=_sanitize_connector_config(row.config_json),
                credentials_json={},
                last_validation_ok=row.last_validation_ok,
                last_validation_error=row.last_validation_error,
                last_validated_at=row.last_validated_at,
                telemetry_json=row.telemetry_json or {},
                last_sync_at=row.last_sync_at,
                credentials_keys_configured=cred_keys,
            )
        )
    db.commit()
    return sorted(out, key=lambda x: x.connector_name)


@router.post("/connectors/{connector_name}/validate", response_model=ConnectorConfigOut)
def validate_connector_config(
    connector_name: str,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(require_tenant_admin_or_superadmin),
):
    key = connector_name.strip().lower()
    if key not in _CONNECTORS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not supported")
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    row = db.execute(
        select(TenantConnectorConfig).where(
            TenantConnectorConfig.tenant_id == tenant.id, TenantConnectorConfig.connector_name == key
        )
    ).scalar_one_or_none()
    if row is None:
        row = TenantConnectorConfig(tenant_id=tenant.id, connector_name=key, enabled=False, config_json={})
        db.add(row)
    cfg = row.config_json or {}
    # Lightweight validation for fast feedback; connector runtime uses richer behavior.
    err: Optional[str] = None
    if key == "github" and row.enabled and not cfg.get("repo"):
        err = "github.repo is required when connector is enabled"
    if key == "gitlab" and row.enabled and not cfg.get("project_id"):
        err = "gitlab.project_id is required when connector is enabled"
    if key == "jira" and row.enabled and ((not cfg.get("project") and not cfg.get("project_key")) or not cfg.get("base_url")):
        err = "jira.base_url and jira.project (or project_key) are required when connector is enabled"
    if key == "finops" and row.enabled and not cfg.get("cost_file"):
        err = "finops.cost_file is required when connector is enabled"
    if key == "azure" and row.enabled and (not cfg.get("organization") or not cfg.get("project")):
        err = "azure.organization and azure.project are required when connector is enabled"
    if key == "aws" and row.enabled and not cfg.get("account_id"):
        err = "aws.account_id is required when connector is enabled"
    if key == "vps" and row.enabled and (not cfg.get("provider") or not cfg.get("host")):
        err = "vps.provider and vps.host are required when connector is enabled"
    row.last_validated_at = datetime.now(timezone.utc)
    row.last_validation_ok = err is None
    row.last_validation_error = err
    _audit(
        db,
        tenant_id=tenant.id,
        actor_user_id=current.id,
        area="connectors",
        action="validate",
        target_key=key,
        before_json=None,
        after_json={"last_validation_ok": row.last_validation_ok, "last_validation_error": row.last_validation_error},
    )
    db.commit()
    return ConnectorConfigOut(
        connector_name=key,
        enabled=row.enabled,
        config_json=_sanitize_connector_config(row.config_json),
        credentials_json={},
        last_validation_ok=row.last_validation_ok,
        last_validation_error=row.last_validation_error,
        last_validated_at=row.last_validated_at,
        telemetry_json=row.telemetry_json or {},
        last_sync_at=row.last_sync_at,
    )


@router.get("/ai/providers", response_model=ProviderSetOut)
def get_ai_provider_configs(
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    settings_row = db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)).scalar_one_or_none()
    rows = (
        db.execute(select(TenantAIProviderConfig).where(TenantAIProviderConfig.tenant_id == tenant.id))
        .scalars()
        .all()
    )
    by_name = {r.provider_name: r for r in rows}
    out: list[ProviderConfigOut] = []
    for name in sorted(_PROVIDERS):
        r = by_name.get(name)
        out.append(
            ProviderConfigOut(
                provider_name=name,
                enabled=bool(r.enabled) if r else False,
                model_name=r.model_name if r else None,
                temperature=r.temperature if r else None,
                max_tokens=r.max_tokens if r else None,
                endpoint_url=r.endpoint_url if r else None,
                api_key_ref=_mask_api_key_ref(r.api_key_ref) if r else None,
                api_key=None,
                timeout_seconds=r.timeout_seconds if r else None,
                retry_count=r.retry_count if r else None,
                metadata_json=r.metadata_json if r else {},
                last_validation_ok=r.last_validation_ok if r else None,
                last_validation_error=r.last_validation_error if r else None,
                last_validated_at=r.last_validated_at if r else None,
            )
        )
    return ProviderSetOut(default_provider=settings_row.default_ai_provider if settings_row else None, providers=out)


@router.put("/ai/providers", response_model=ProviderSetOut)
def put_ai_provider_configs(
    body: ProviderSetBody,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(require_tenant_admin_or_superadmin),
):
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    settings_row = db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)).scalar_one_or_none()
    if settings_row is None:
        settings_row = TenantSettings(tenant_id=tenant.id, default_ai_provider=None, ui_preferences={}, rag_config_json={})
        db.add(settings_row)
    if body.default_provider is not None:
        settings_row.default_ai_provider = body.default_provider

    for name, cfg in body.providers.items():
        key = name.strip().lower()
        if key not in _PROVIDERS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"provider '{name}' is unsupported",
            )
        row = db.execute(
            select(TenantAIProviderConfig).where(
                TenantAIProviderConfig.tenant_id == tenant.id, TenantAIProviderConfig.provider_name == key
            )
        ).scalar_one_or_none()
        before = None
        if row is None:
            row = TenantAIProviderConfig(tenant_id=tenant.id, provider_name=key)
            db.add(row)
        else:
            before = {
                "enabled": row.enabled,
                "model_name": row.model_name,
                "temperature": row.temperature,
                "max_tokens": row.max_tokens,
                "endpoint_url": row.endpoint_url,
                "api_key_ref": _mask_api_key_ref(row.api_key_ref),
            }
        row.enabled = cfg.enabled
        row.model_name = cfg.model_name.strip() if cfg.model_name else None
        row.temperature = cfg.temperature
        row.max_tokens = cfg.max_tokens
        row.endpoint_url = cfg.endpoint_url
        row.api_key_ref = cfg.api_key_ref
        row.api_key_encrypted = encrypt_json({"api_key": cfg.api_key}, secret=get_settings().app_encryption_key) if cfg.api_key else None
        row.timeout_seconds = cfg.timeout_seconds
        row.retry_count = cfg.retry_count
        row.metadata_json = cfg.metadata_json
        row.last_validation_ok = None
        row.last_validation_error = None
        row.last_validated_at = None
        _audit(
            db,
            tenant_id=tenant.id,
            actor_user_id=current.id,
            area="ai_providers",
            action="upsert",
            target_key=key,
            before_json=before,
            after_json={
                "enabled": row.enabled,
                "model_name": row.model_name,
                "temperature": row.temperature,
                "max_tokens": row.max_tokens,
                "endpoint_url": row.endpoint_url,
                "api_key_ref": _mask_api_key_ref(row.api_key_ref),
            },
        )

    db.commit()
    return get_ai_provider_configs(tenant_slug=tenant.slug, db=db, current=current)


@router.post("/ai/providers/{provider_name}/validate", response_model=ProviderConfigOut)
def validate_ai_provider_config(
    provider_name: str,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(require_tenant_admin_or_superadmin),
):
    key = provider_name.strip().lower()
    if key not in _PROVIDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not supported")
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    row = db.execute(
        select(TenantAIProviderConfig).where(
            TenantAIProviderConfig.tenant_id == tenant.id, TenantAIProviderConfig.provider_name == key
        )
    ).scalar_one_or_none()
    if row is None:
        row = TenantAIProviderConfig(tenant_id=tenant.id, provider_name=key, enabled=False, metadata_json={})
        db.add(row)
    err: Optional[str] = None
    if row.enabled and not row.model_name:
        err = "model_name is required when provider is enabled"
    if row.enabled and not (row.api_key_ref or row.api_key_encrypted) and key != "ollama":
        err = "api_key_ref or api_key is required when provider is enabled"
    if row.enabled and key == "azure_openai" and not row.endpoint_url:
        err = "endpoint_url is required for azure_openai when enabled"
    if row.enabled and key == "aws_bedrock":
        region = (row.metadata_json or {}).get("region")
        if not region:
            err = "metadata_json.region is required for aws_bedrock when enabled"
        elif not err:
            err = "aws_bedrock runtime invocation is not implemented in this release"
    # Lightweight reachability test (401/403 still means endpoint is reachable)
    if row.enabled and not err and row.endpoint_url:
        try:
            resp = httpx.get(row.endpoint_url, timeout=3.0)
            if resp.status_code >= 500:
                err = f"endpoint returned server error {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            err = f"endpoint connection failed: {exc}"
    row.last_validated_at = datetime.now(timezone.utc)
    row.last_validation_ok = err is None
    row.last_validation_error = err
    _audit(
        db,
        tenant_id=tenant.id,
        actor_user_id=current.id,
        area="ai_providers",
        action="validate",
        target_key=key,
        before_json=None,
        after_json={"last_validation_ok": row.last_validation_ok, "last_validation_error": row.last_validation_error},
    )
    db.commit()
    return ProviderConfigOut(
        provider_name=key,
        enabled=row.enabled,
        model_name=row.model_name,
        temperature=row.temperature,
        max_tokens=row.max_tokens,
        endpoint_url=row.endpoint_url,
        api_key_ref=_mask_api_key_ref(row.api_key_ref),
        api_key=None,
        timeout_seconds=row.timeout_seconds,
        retry_count=row.retry_count,
        metadata_json=row.metadata_json,
        last_validation_ok=row.last_validation_ok,
        last_validation_error=row.last_validation_error,
        last_validated_at=row.last_validated_at,
    )


def _digest_schedule_out(raw: dict[str, Any] | None) -> DigestScheduleOut:
    data = raw if isinstance(raw, dict) else {}
    recipients = data.get("recipients")
    return DigestScheduleOut(
        daily_enabled=bool(data.get("daily_enabled", False)),
        daily_time_utc=str(data.get("daily_time_utc") or "08:00"),
        weekly_enabled=bool(data.get("weekly_enabled", False)),
        weekly_day=str(data.get("weekly_day") or "monday"),
        weekly_time_utc=str(data.get("weekly_time_utc") or "08:00"),
        recipients=[str(x).strip() for x in recipients if str(x).strip()] if isinstance(recipients, list) else [],
    )


def _channels_out(row: TenantNotificationConfig | None) -> dict[str, NotificationChannelToggles]:
    raw = row.notification_channels_json if row and isinstance(row.notification_channels_json, dict) else {}
    out: dict[str, NotificationChannelToggles] = {}
    for event_type, defaults in DEFAULT_CHANNELS.items():
        event_cfg = raw.get(event_type) if isinstance(raw.get(event_type), dict) else {}
        out[event_type] = NotificationChannelToggles(
            email=bool(event_cfg.get("email", defaults.get("email", True))),
            slack=bool(event_cfg.get("slack", defaults.get("slack", False))),
            teams=bool(event_cfg.get("teams", defaults.get("teams", False))),
        )
    return out


@router.get("/notifications", response_model=NotificationConfigOut)
def get_notification_config(
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    row = db.execute(select(TenantNotificationConfig).where(TenantNotificationConfig.tenant_id == tenant.id)).scalar_one_or_none()
    templates = resolved_templates(row)
    emails: list[str] = []
    if row:
        raw = row.governance_run_notify_emails_json
        if isinstance(raw, list):
            emails = [str(x).strip() for x in raw if str(x).strip()]
    smtp = resolve_smtp_dataclass(db, tenant.id)
    platform_row = db.execute(select(PlatformNotificationConfig).order_by(PlatformNotificationConfig.id.asc())).scalars().first()
    platform_configured = bool(
        platform_row
        and platform_row.smtp_host
        and platform_row.smtp_port
        and platform_row.notifications_enabled
    )
    return NotificationConfigOut(
        smtp_host=row.smtp_host if row else None,
        smtp_port=row.smtp_port if row else None,
        smtp_username=row.smtp_username if row else None,
        smtp_password_configured=bool(row and row.smtp_password_encrypted),
        smtp_from_email=row.smtp_from_email if row else None,
        use_tls=row.use_tls if row else True,
        use_ssl=row.use_ssl if row else False,
        notifications_enabled=row.notifications_enabled if row else False,
        using_platform_smtp=smtp.source == "platform",
        platform_smtp_configured=platform_configured,
        slack_webhook_configured=bool(row and row.slack_incoming_webhook_encrypted),
        teams_webhook_configured=bool(row and row.teams_incoming_webhook_encrypted),
        governance_notify_on_run_complete=bool(row and row.governance_notify_on_run_complete),
        governance_run_notify_emails=emails,
        notification_channels=_channels_out(row),
        digest_schedule=_digest_schedule_out(row.digest_schedule_json if row else None),
        templates={
            k: NotificationTemplateOut(subject=v["subject"], body=v.get("body_text") or v.get("body", ""))
            for k, v in templates.items()
        },
        last_test_ok=row.last_test_ok if row else None,
        last_test_error=row.last_test_error if row else None,
        last_tested_at=row.last_tested_at if row else None,
    )


@router.put("/notifications", response_model=NotificationConfigOut)
def put_notification_config(
    body: NotificationConfigIn,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(require_tenant_admin_or_superadmin),
):
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    row = _get_or_create_notification_config(db, tenant.id)
    row.smtp_host = body.smtp_host
    row.smtp_port = body.smtp_port
    row.smtp_username = body.smtp_username
    if body.smtp_password:
        row.smtp_password_encrypted = encrypt_json({"password": body.smtp_password}, secret=get_settings().app_encryption_key)
    row.smtp_from_email = body.smtp_from_email
    row.use_tls = body.use_tls
    row.use_ssl = body.use_ssl
    row.notifications_enabled = body.notifications_enabled
    row.templates_json = {
        k: {
            "subject": v.subject,
            "body_text": v.body,
            "body_html": v.body.replace("\n", "<br/>"),
        }
        for k, v in body.templates.items()
    }
    if body.clear_slack_incoming_webhook:
        row.slack_incoming_webhook_encrypted = None
    elif body.slack_incoming_webhook:
        row.slack_incoming_webhook_encrypted = encrypt_json(
            {"url": body.slack_incoming_webhook.strip()},
            secret=get_settings().app_encryption_key,
        )
    if body.clear_teams_incoming_webhook:
        row.teams_incoming_webhook_encrypted = None
    elif body.teams_incoming_webhook:
        row.teams_incoming_webhook_encrypted = encrypt_json(
            {"url": body.teams_incoming_webhook.strip()},
            secret=get_settings().app_encryption_key,
        )
    row.governance_notify_on_run_complete = body.governance_notify_on_run_complete
    row.governance_run_notify_emails_json = [e.strip().lower() for e in body.governance_run_notify_emails if e.strip()]
    if body.notification_channels:
        row.notification_channels_json = {
            k: {"email": v.email, "slack": v.slack, "teams": v.teams}
            for k, v in body.notification_channels.items()
        }
    if body.digest_schedule is not None:
        row.digest_schedule_json = body.digest_schedule.model_dump()
    _audit(
        db,
        tenant_id=tenant.id,
        actor_user_id=current.id,
        area="notifications",
        action="upsert",
        target_key="smtp",
        before_json=None,
        after_json={"smtp_host": row.smtp_host, "smtp_port": row.smtp_port, "notifications_enabled": row.notifications_enabled},
    )
    db.commit()
    return get_notification_config(tenant_slug=tenant.slug, db=db, current=current)

from app.services.notification_router import _decrypt_webhook_url
from app.services.slack_notifier import send_slack_message

@router.post("/notifications/test")
def test_notification_config(
    body: NotificationTestIn,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(require_tenant_admin_or_superadmin),
):
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    row = _get_or_create_notification_config(db, tenant.id)
    try:
        if body.test_slack:
            slack_url = body.slack_webhook.strip() if body.slack_webhook else None
            if not slack_url:
                slack_url = _decrypt_webhook_url(row.slack_incoming_webhook_encrypted)
            if not slack_url:
                platform_row = db.execute(select(PlatformNotificationConfig)).scalar_one_or_none()
                if platform_row:
                    slack_url = _decrypt_webhook_url(platform_row.slack_incoming_webhook_encrypted)
            if not slack_url:
                raise ValueError("No Slack webhook configured on tenant or platform.")
            send_slack_message(slack_url, title="Webhook Test", body="This is a test notification from the workspace settings.", fields=[])
            return {"ok": True, "message": "Slack webhook test succeeded"}

        test_smtp_connection(row)
        if body.to_email:
            send_templated_email(
                row,
                template_key="user_welcome",
                to_email=body.to_email,
                values={"user_email": body.to_email, "tenant_slug": tenant.slug, "temporary_password": "test-password"},
            )
        row.last_test_ok = True
        row.last_test_error = None
        row.last_tested_at = datetime.now(timezone.utc)
        db.commit()
        return {"ok": True, "message": "SMTP test succeeded"}
    except Exception as exc:  # noqa: BLE001
        if not body.test_slack:
            row.last_test_ok = False
            row.last_test_error = str(exc)
            row.last_tested_at = datetime.now(timezone.utc)
        return {"ok": False, "message": f"Test failed: {exc}"}


@router.get("/connectors/github/repos")
def get_github_repos(
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    row = db.execute(
        select(TenantConnectorConfig).where(
            TenantConnectorConfig.tenant_id == tenant.id, TenantConnectorConfig.connector_name == "github"
        )
    ).scalar_one_or_none()
    if not row or not row.enabled:
        raise HTTPException(status_code=400, detail="GitHub connector not enabled")
    
    encryption_key = get_settings().app_encryption_key
    try:
        cred = decrypt_json(row.encrypted_credentials_json, secret=encryption_key) if row.encrypted_credentials_json else {}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to decrypt credentials")
    
    token = cred.get("token") or row.config_json.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="GitHub token not configured")
    
    token = token.strip()
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AAF-AppTestify"
    }
    
    try:
        resp = httpx.get("https://api.github.com/user/repos?per_page=100", headers=headers, timeout=10.0)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"GitHub API error: {resp.text}")
        repos_data = resp.json()
        return [r.get("full_name") for r in repos_data if r.get("full_name")]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repositories: {e}")


@router.get("/connectors/github/branches")
def get_github_branches(
    repo: str = Query(...),
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    row = db.execute(
        select(TenantConnectorConfig).where(
            TenantConnectorConfig.tenant_id == tenant.id, TenantConnectorConfig.connector_name == "github"
        )
    ).scalar_one_or_none()
    if not row or not row.enabled:
        raise HTTPException(status_code=400, detail="GitHub connector not enabled")
    
    if "/" not in repo:
        raise HTTPException(status_code=400, detail="Invalid repo name")
        
    encryption_key = get_settings().app_encryption_key
    try:
        cred = decrypt_json(row.encrypted_credentials_json, secret=encryption_key) if row.encrypted_credentials_json else {}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to decrypt credentials")
    
    token = cred.get("token") or row.config_json.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="GitHub token not configured")
        
    token = token.strip()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AAF-AppTestify"
    }
    
    try:
        owner, name = repo.split("/", 1)
        resp = httpx.get(f"https://api.github.com/repos/{owner}/{name}/branches?per_page=100", headers=headers, timeout=10.0)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"GitHub API error: {resp.text}")
        branches_data = resp.json()
        return [b.get("name") for b in branches_data if b.get("name")]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch branches: {e}")


@router.get("/connectors/jira/projects")
def get_jira_projects(
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    row = db.execute(
        select(TenantConnectorConfig).where(
            TenantConnectorConfig.tenant_id == tenant.id, TenantConnectorConfig.connector_name == "jira"
        )
    ).scalar_one_or_none()
    if not row or not row.enabled:
        raise HTTPException(status_code=400, detail="Jira connector not enabled")
        
    cfg = row.config_json or {}
    base_url = cfg.get("base_url")
    if not base_url:
        raise HTTPException(status_code=400, detail="Jira base URL not configured")
        
    if isinstance(base_url, str) and "atlassian.net" in base_url:
        import re
        match = re.search(r"(https?://[^\/]+\.atlassian\.net)", base_url)
        if match:
            base_url = match.group(1)

    encryption_key = get_settings().app_encryption_key
    try:
        cred = decrypt_json(row.encrypted_credentials_json, secret=encryption_key) if row.encrypted_credentials_json else {}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to decrypt credentials")
        
    email = cred.get("email") or cfg.get("email")
    token = cred.get("token") or cfg.get("token") or cred.get("api_token") or cfg.get("api_token")
    
    if not email or not token:
        raise HTTPException(status_code=400, detail="Jira email or token not configured")
        
    email = email.strip()
    token = token.strip()

    auth = (email, token)
    url = f"{base_url.rstrip('/')}/rest/api/3/project"
    
    try:
        resp = httpx.get(url, auth=auth, timeout=10.0)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"Jira API error: {resp.text}")
        projects_data = resp.json()
        return [{"key": p.get("key"), "name": p.get("name")} for p in projects_data if p.get("key")]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch projects: {e}")


@router.get("/connectors/jira/boards")
def get_jira_boards(
    project_key: Optional[str] = Query(default=None),
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    row = db.execute(
        select(TenantConnectorConfig).where(
            TenantConnectorConfig.tenant_id == tenant.id, TenantConnectorConfig.connector_name == "jira"
        )
    ).scalar_one_or_none()
    if not row or not row.enabled:
        raise HTTPException(status_code=400, detail="Jira connector not enabled")
        
    cfg = row.config_json or {}
    base_url = cfg.get("base_url")
    if not base_url:
        raise HTTPException(status_code=400, detail="Jira base URL not configured")
        
    if isinstance(base_url, str) and "atlassian.net" in base_url:
        import re
        match = re.search(r"(https?://[^\/]+\.atlassian\.net)", base_url)
        if match:
            base_url = match.group(1)

    encryption_key = get_settings().app_encryption_key
    try:
        cred = decrypt_json(row.encrypted_credentials_json, secret=encryption_key) if row.encrypted_credentials_json else {}
    except Exception:
        raise HTTPException(status_code=500, detail=f"Failed to decrypt credentials")
        
    email = cred.get("email") or cfg.get("email")
    token = cred.get("token") or cfg.get("token") or cred.get("api_token") or cfg.get("api_token")
    
    if not email or not token:
        raise HTTPException(status_code=400, detail="Jira email or token not configured")
        
    email = email.strip()
    token = token.strip()

    auth = (email, token)
    url = f"{base_url.rstrip('/')}/rest/agile/1.0/board"
    params = {}
    if project_key:
        params["projectKeyOrId"] = project_key
        
    try:
        resp = httpx.get(url, auth=auth, params=params, timeout=10.0)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"Jira Agile API error: {resp.text}")
        boards_data = resp.json()
        values = boards_data.get("values") or []
        return [{"id": str(b.get("id")), "name": b.get("name"), "type": b.get("type")} for b in values if b.get("id")]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch boards: {e}")
