"""Cloud integration signal fetchers with live/simulated fallback."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.config import TenantConnectorConfig
from app.security import decrypt_json
from app.services.azure_live import fetch_azure_signal
from app.services.github_live import fetch_github_signal
from app.services.http_resilience import IntegrationFetchError
from app.services.jira_live import fetch_jira_signal
from aaf.config import get_settings


def connector_signal(connector: TenantConnectorConfig) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    name = connector.connector_name
    enabled = bool(connector.enabled)
    if not enabled:
        return {
            "connector": name,
            "enabled": False,
            "freshness": "disabled",
            "latency_ms": None,
            "errors_24h": 0,
            "summary": f"{name} connector disabled",
            "captured_at": now,
        }

    def _fallback(connector_name: str, category: str, message: str) -> dict[str, Any]:
        return {
            "connector": connector_name,
            "enabled": True,
            "mode": "fallback_error",
            "error_category": category,
            "error_message": message,
            "freshness": "degraded",
            "latency_ms": None,
            "errors_24h": None,
            "captured_at": now,
        }

    if name == "azure":
        cfg = connector.config_json or {}
        creds = {}
        try:
            creds = decrypt_json(connector.encrypted_credentials_json, secret=get_settings().app_encryption_key)
        except Exception:  # noqa: BLE001
            creds = {}
        if cfg.get("organization") and cfg.get("project"):
            try:
                return fetch_azure_signal(
                    organization=str(cfg.get("organization")),
                    project=str(cfg.get("project")),
                    pat=str(creds.get("token")) if isinstance(creds, dict) and creds.get("token") else None,
                )
            except IntegrationFetchError as e:
                return _fallback("azure", e.category, str(e))
            except Exception as e:  # noqa: BLE001
                return _fallback("azure", "unknown", str(e))
        return {
            "connector": "azure",
            "enabled": True,
            "mode": "unconfigured",
            "freshness": "unknown",
            "latency_ms": None,
            "errors_24h": None,
            "error_category": "config",
            "error_message": "azure requires config_json.organization and config_json.project for live telemetry",
            "captured_at": now,
        }
    if name == "aws":
        cfg = connector.config_json or {}
        account = str(cfg.get("account_id") or "")
        return {
            "connector": "aws",
            "enabled": True,
            "mode": "not_implemented",
            "freshness": "unknown",
            "latency_ms": None,
            "errors_24h": None,
            "account_scope": account or None,
            "error_category": "unsupported",
            "error_message": "live aws connector telemetry not implemented yet",
            "captured_at": now,
        }
    if name == "github":
        cfg = connector.config_json or {}
        if cfg.get("repo"):
            try:
                creds = decrypt_json(connector.encrypted_credentials_json, secret=get_settings().app_encryption_key)
                token = creds.get("token") if isinstance(creds, dict) else None
                return fetch_github_signal(str(cfg["repo"]), token=token)
            except IntegrationFetchError as e:
                return _fallback("github", e.category, str(e))
            except Exception as e:  # noqa: BLE001
                return _fallback("github", "unknown", str(e))
        return {
            "connector": "github",
            "enabled": True,
            "mode": "unconfigured",
            "freshness": "unknown",
            "latency_ms": None,
            "errors_24h": None,
            "error_category": "config",
            "error_message": "github requires config_json.repo for live telemetry",
            "captured_at": now,
        }
    if name == "jira":
        cfg = connector.config_json or {}
        project = str(cfg.get("project") or "")
        creds = {}
        try:
            creds = decrypt_json(connector.encrypted_credentials_json, secret=get_settings().app_encryption_key)
        except Exception:  # noqa: BLE001
            creds = {}
        if project and cfg.get("base_url"):
            try:
                return fetch_jira_signal(
                    base_url=str(cfg.get("base_url")),
                    project_key=project,
                    email=str(creds.get("email")) if isinstance(creds, dict) and creds.get("email") else None,
                    api_token=str(creds.get("token")) if isinstance(creds, dict) and creds.get("token") else None,
                )
            except IntegrationFetchError as e:
                return _fallback("jira", e.category, str(e))
            except Exception as e:  # noqa: BLE001
                return _fallback("jira", "unknown", str(e))
        return {
            "connector": "jira",
            "enabled": True,
            "mode": "unconfigured",
            "freshness": "unknown",
            "latency_ms": None,
            "errors_24h": None,
            "error_category": "config",
            "error_message": "jira requires config_json.base_url and config_json.project for live telemetry",
            "captured_at": now,
        }
    return {
        "connector": name,
        "enabled": True,
        "freshness": "unknown",
        "latency_ms": None,
        "errors_24h": 0,
        "captured_at": now,
    }
