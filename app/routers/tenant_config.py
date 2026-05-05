"""Tenant-scoped settings, connector, and AI provider configuration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_active_user, require_tenant_admin_or_superadmin
from app.models.config import ConfigAuditLog, TenantAIProviderConfig, TenantConnectorConfig, TenantSettings
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/tenant", tags=["tenant-config"])

_CONNECTORS = {"github", "jira", "finops"}
_PROVIDERS = {"openai", "anthropic", "azure_openai"}
_SECRET_KEYS = {"token", "api_token", "password", "secret", "key"}


class TenantSettingsOut(BaseModel):
    tenant_slug: str
    default_ai_provider: Optional[str] = None
    ui_preferences: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class TenantSettingsPatch(BaseModel):
    default_ai_provider: Optional[str] = None
    ui_preferences: Optional[dict[str, Any]] = None

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


class ConnectorConfigOut(ConnectorConfigIn):
    connector_name: str
    last_validation_ok: Optional[bool] = None
    last_validation_error: Optional[str] = None
    last_validated_at: Optional[datetime] = None


class ConnectorSetBody(BaseModel):
    connectors: dict[str, ConnectorConfigIn] = Field(default_factory=dict)


class ProviderConfigIn(BaseModel):
    enabled: bool = False
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    endpoint_url: Optional[str] = None
    api_key_ref: Optional[str] = None
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


@router.get("/settings", response_model=TenantSettingsOut)
def get_tenant_settings(
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    tenant = _resolve_tenant_for_user(db, current, tenant_slug)
    settings = db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)).scalar_one_or_none()
    if settings is None:
        return TenantSettingsOut(tenant_slug=tenant.slug, default_ai_provider=None, ui_preferences={})
    return TenantSettingsOut(
        tenant_slug=tenant.slug,
        default_ai_provider=settings.default_ai_provider,
        ui_preferences=settings.ui_preferences or {},
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
        row = TenantSettings(tenant_id=tenant.id, default_ai_provider=None, ui_preferences={})
        db.add(row)
    else:
        before = {"default_ai_provider": row.default_ai_provider, "ui_preferences": row.ui_preferences}

    payload = body.model_dump(exclude_unset=True)
    if "default_ai_provider" in payload:
        row.default_ai_provider = payload["default_ai_provider"]
    if "ui_preferences" in payload and payload["ui_preferences"] is not None:
        row.ui_preferences = payload["ui_preferences"]
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
    for name in sorted(_CONNECTORS):
        r = by_name.get(name)
        out.append(
            ConnectorConfigOut(
                connector_name=name,
                enabled=bool(r.enabled) if r else False,
                config_json=_sanitize_connector_config(r.config_json) if r else {},
                last_validation_ok=r.last_validation_ok if r else None,
                last_validation_error=r.last_validation_error if r else None,
                last_validated_at=r.last_validated_at if r else None,
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
        row.config_json = cfg.config_json
        row.last_validation_error = None
        row.last_validation_ok = None
        row.last_validated_at = None
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
                last_validation_ok=row.last_validation_ok,
                last_validation_error=row.last_validation_error,
                last_validated_at=row.last_validated_at,
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
    if key == "jira" and row.enabled and not cfg.get("project"):
        err = "jira.project is required when connector is enabled"
    if key == "finops" and row.enabled and not cfg.get("cost_file"):
        err = "finops.cost_file is required when connector is enabled"
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
        last_validation_ok=row.last_validation_ok,
        last_validation_error=row.last_validation_error,
        last_validated_at=row.last_validated_at,
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
        settings_row = TenantSettings(tenant_id=tenant.id, default_ai_provider=None, ui_preferences={})
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
        row.model_name = cfg.model_name
        row.temperature = cfg.temperature
        row.max_tokens = cfg.max_tokens
        row.endpoint_url = cfg.endpoint_url
        row.api_key_ref = cfg.api_key_ref
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
    if row.enabled and not row.api_key_ref:
        err = "api_key_ref is required when provider is enabled"
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
        timeout_seconds=row.timeout_seconds,
        retry_count=row.retry_count,
        metadata_json=row.metadata_json,
        last_validation_ok=row.last_validation_ok,
        last_validation_error=row.last_validation_error,
        last_validated_at=row.last_validated_at,
    )
