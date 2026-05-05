"""Resolve effective runtime configuration for a tenant with env fallback."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from aaf.config import ConnectorMode, Settings
from app.models.config import TenantAIProviderConfig, TenantConnectorConfig, TenantSettings
from app.models.tenant import Tenant
from app.models.user import User


def resolve_tenant_for_user(db: Session, user: User, tenant_slug: Optional[str] = None) -> Optional[Tenant]:
    """Resolve tenant context for request-scoped operations."""
    if user.is_superadmin:
        if tenant_slug:
            return db.execute(select(Tenant).where(Tenant.slug == tenant_slug.strip().lower())).scalar_one_or_none()
        return db.execute(select(Tenant).order_by(Tenant.slug)).scalars().first()
    if user.tenant_id is None:
        return None
    return db.get(Tenant, user.tenant_id)


def resolve_effective_settings(db: Session, base: Settings, tenant: Optional[Tenant]) -> Settings:
    """Return settings with tenant-specific connector overrides merged over env defaults."""
    if tenant is None:
        return base

    merged = base.model_copy(deep=True)
    rows = (
        db.execute(select(TenantConnectorConfig).where(TenantConnectorConfig.tenant_id == tenant.id))
        .scalars()
        .all()
    )
    enabled_any = False
    for row in rows:
        if not row.enabled:
            continue
        enabled_any = True
        cfg = row.config_json or {}
        name = row.connector_name
        if name == "github":
            if cfg.get("repo"):
                merged.github_repo = str(cfg["repo"])
            if cfg.get("token"):
                merged.github_token = str(cfg["token"])
        elif name == "jira":
            if cfg.get("url"):
                merged.jira_url = str(cfg["url"])
            if cfg.get("email"):
                merged.jira_email = str(cfg["email"])
            if cfg.get("api_token"):
                merged.jira_api_token = str(cfg["api_token"])
        elif name == "finops":
            if cfg.get("cost_file"):
                from pathlib import Path

                merged.finops_cost_file = Path(str(cfg["cost_file"]))
    if enabled_any:
        merged.connector_mode = ConnectorMode.LIVE
    return merged


def get_ai_runtime_summary(db: Session, tenant: Optional[Tenant]) -> dict[str, Any]:
    """Return safe AI provider config summary for UI/debug responses."""
    if tenant is None:
        return {"default_provider": None, "providers": []}
    s = db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)).scalar_one_or_none()
    providers = (
        db.execute(select(TenantAIProviderConfig).where(TenantAIProviderConfig.tenant_id == tenant.id))
        .scalars()
        .all()
    )
    return {
        "default_provider": s.default_ai_provider if s else None,
        "providers": [
            {
                "provider_name": p.provider_name,
                "enabled": p.enabled,
                "model_name": p.model_name,
                "temperature": p.temperature,
                "max_tokens": p.max_tokens,
                "endpoint_url": p.endpoint_url,
                "api_key_ref": _mask_ref(p.api_key_ref),
            }
            for p in providers
        ],
    }


def _mask_ref(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}***{value[-2:]}"
