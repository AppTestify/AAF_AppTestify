"""Resolve effective runtime configuration for a tenant with env fallback."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from aaf.config import ConnectorMode, Settings
from app.models.config import TenantAIProviderConfig, TenantConnectorConfig, TenantSettings
from app.models.tenant import Tenant
from app.models.user import User


import logging

from app.security import decrypt_json

_log = logging.getLogger("aaf.config")


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
    encryption_key = base.app_encryption_key

    for row in rows:
        if not row.enabled:
            continue
        enabled_any = True
        cfg = row.config_json or {}
        # Decrypt credentials if they exist
        try:
            cred = (
                decrypt_json(row.encrypted_credentials_json, secret=encryption_key)
                if row.encrypted_credentials_json
                else {}
            )
        except Exception:
            _log.exception(f"Failed to decrypt credentials for connector {row.connector_name}")
            cred = {}

        name = row.connector_name
        try:
            if name == "github":
                # Support both config and credentials for token
                repo = cfg.get("repo") or cfg.get("repository")
                if repo:
                    merged.github_repo = str(repo)
                token = cred.get("token") or cfg.get("token")
                if token:
                    merged.github_token = str(token)
            elif name == "jira":
                url = cfg.get("base_url") or cfg.get("url")
                if url:
                    # Advanced sanitization: extract domain only if it's an Atlassian URL
                    url_str = str(url).strip().lower().rstrip("/")
                    if ".atlassian.net" in url_str:
                        # Extract https://domain.atlassian.net
                        parts = url_str.split(".atlassian.net")
                        base_part = parts[0].split("://")[-1]
                        scheme = "https" if "https" in url_str else "http"
                        url_str = f"{scheme}://{base_part}.atlassian.net"
                    elif "://" not in url_str:
                        url_str = f"https://{url_str}"
                    merged.jira_url = url_str
                email = cred.get("email") or cfg.get("email")
                if email:
                    merged.jira_email = str(email)
                token = cred.get("token") or cfg.get("token") or cfg.get("api_token")
                if token:
                    merged.jira_api_token = str(token)
                project = cfg.get("project") or cfg.get("project_key")
                if project:
                    merged.jira_project = str(project)
                board = cfg.get("board_id")
                if board:
                    merged.jira_board_id = str(board)
            elif name == "aws":
                region = cfg.get("region")
                if region:
                    merged.aws_region = str(region)
                key = cred.get("access_key_id") or cred.get("aws_access_key_id")
                secret = cred.get("secret_access_key") or cred.get("aws_secret_access_key")
                if key:
                    merged.aws_access_key_id = str(key)
                if secret:
                    merged.aws_secret_access_key = str(secret)
            elif name == "finops":
                if cfg.get("cost_file"):
                    from pathlib import Path
                    merged.finops_cost_file = Path(str(cfg["cost_file"]))
            elif name == "gitlab":
                url = cfg.get("gitlab_url") or cfg.get("url")
                if url:
                    merged.gitlab_url = str(url)
                token = cred.get("token") or cfg.get("token") or cred.get("gitlab_token") or cfg.get("gitlab_token")
                if token:
                    merged.gitlab_token = str(token)
                project = cfg.get("project_id") or cfg.get("gitlab_project_id") or cfg.get("project")
                if project:
                    merged.gitlab_project_id = str(project).strip()
            elif name == "azure":
                org = cfg.get("organization") or cfg.get("org")
                if org:
                    merged.azure_organization = str(org)
                project = cfg.get("project")
                if project:
                    merged.azure_project = str(project)
                repo = cfg.get("repo") or cfg.get("repository")
                if repo:
                    merged.azure_repo = str(repo)
                pat = cred.get("token") or cfg.get("token") or cred.get("pat")
                if pat:
                    merged.azure_pat = str(pat)
        except Exception:
            _log.exception(f"Error merging config for connector {name}")
            
    if enabled_any:
        merged.connector_mode = ConnectorMode.LIVE
    return merged


def apply_pipeline_overrides(settings: Settings, tenant_settings: Optional[TenantSettings]) -> Settings:
    """Merge tenant UI governance_pipeline / pipeline_overrides into Settings (tau, weights, RAR)."""
    if tenant_settings is None:
        return settings
    prefs = tenant_settings.ui_preferences or {}
    ov = prefs.get("governance_pipeline") or prefs.get("pipeline_overrides")
    if not isinstance(ov, dict) or not ov:
        return settings
    updates: dict[str, Any] = {}
    for key in (
        "tau_consensus",
        "max_rar_loops",
        "rar_live_refresh_enabled",
        "w_perf",
        "w_cost",
        "w_risk",
    ):
        if key not in ov:
            continue
        val = ov[key]
        if key == "rar_live_refresh_enabled":
            updates[key] = bool(val)
        elif key == "max_rar_loops":
            updates[key] = int(val)
        elif key == "tau_consensus":
            updates[key] = float(val)
        elif key in ("w_perf", "w_cost", "w_risk"):
            updates[key] = float(val)
    if not updates:
        return settings
    return settings.model_copy(update=updates)


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
