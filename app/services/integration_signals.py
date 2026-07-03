"""Cloud integration signal fetchers with live/simulated fallback."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.config import TenantConnectorConfig
from app.security import decrypt_json
from app.services.aws_live import fetch_aws_signal
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
        creds = {}
        try:
            creds = decrypt_json(connector.encrypted_credentials_json, secret=get_settings().app_encryption_key)
        except Exception:  # noqa: BLE001
            creds = {}
        region = str(cfg.get("region") or "us-east-1")
        key = str(creds.get("access_key_id") or creds.get("aws_access_key_id") or "") if isinstance(creds, dict) else ""
        secret = str(creds.get("secret_access_key") or creds.get("aws_secret_access_key") or "") if isinstance(creds, dict) else ""
        if key and secret:
            try:
                signal = fetch_aws_signal(region=region, access_key_id=key, secret_access_key=secret)
                signal["account_scope"] = account or None
                return signal
            except Exception as e:  # noqa: BLE001
                return _fallback("aws", "unknown", str(e))
        return {
            "connector": "aws",
            "enabled": True,
            "mode": "unconfigured",
            "freshness": "unknown",
            "latency_ms": None,
            "errors_24h": None,
            "account_scope": account or None,
            "error_category": "config",
            "error_message": "aws requires encrypted credentials (access_key_id, secret_access_key)",
            "captured_at": now,
        }
    if name == "vps":
        cfg = connector.config_json or {}
        provider = str(cfg.get("provider") or "").strip()
        host = str(cfg.get("host") or "").strip()
        status_url = str(cfg.get("status_url") or "").strip()
        creds = {}
        try:
            creds = decrypt_json(connector.encrypted_credentials_json, secret=get_settings().app_encryption_key)
        except Exception:  # noqa: BLE001
            creds = {}
        if not provider or not host:
            return {
                "connector": "vps",
                "enabled": True,
                "mode": "unconfigured",
                "freshness": "unknown",
                "latency_ms": None,
                "errors_24h": None,
                "error_category": "config",
                "error_message": "vps requires config_json.provider and config_json.host for telemetry",
                "captured_at": now,
            }
        if status_url:
            # Optional lightweight health URL check for custom VPS providers.
            import time
            import httpx

            start = time.perf_counter()
            headers = {}
            token = creds.get("token") if isinstance(creds, dict) else None
            if token:
                headers["Authorization"] = f"Bearer {token}"
            try:
                resp = httpx.get(status_url, headers=headers, timeout=5.0)
                latency_ms = (time.perf_counter() - start) * 1000
                return {
                    "connector": "vps",
                    "enabled": True,
                    "mode": "live_http",
                    "provider": provider,
                    "host": host,
                    "status_url": status_url,
                    "freshness": "fresh" if resp.status_code < 400 else "degraded",
                    "latency_ms": round(latency_ms, 2),
                    "errors_24h": 0 if resp.status_code < 400 else 1,
                    "http_status": resp.status_code,
                    "captured_at": now,
                }
            except IntegrationFetchError as e:
                return _fallback("vps", e.category, str(e))
            except Exception as e:  # noqa: BLE001
                return _fallback("vps", "unknown", str(e))
        return {
            "connector": "vps",
            "enabled": True,
            "mode": "configured",
            "provider": provider,
            "host": host,
            "freshness": "unknown",
            "latency_ms": None,
            "errors_24h": None,
            "summary": "VPS connector configured (add status_url for live HTTP health checks)",
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
    if name == "gitlab":
        cfg = connector.config_json or {}
        project = str(cfg.get("project_id") or "").strip()
        creds = {}
        try:
            creds = decrypt_json(connector.encrypted_credentials_json, secret=get_settings().app_encryption_key)
        except Exception:  # noqa: BLE001
            creds = {}
        base_url = str(cfg.get("gitlab_url") or "https://gitlab.com")
        token = str(creds.get("token") or cfg.get("token") or "") if isinstance(creds, dict) else ""
        if project:
            try:
                from app.services.gitlab_live import fetch_gitlab_signal
                return fetch_gitlab_signal(project, token=token or None, base_url=base_url)
            except Exception as e:  # noqa: BLE001
                return _fallback("gitlab", "unknown", str(e))
        return {
            "connector": "gitlab",
            "enabled": True,
            "mode": "unconfigured",
            "freshness": "unknown",
            "latency_ms": None,
            "errors_24h": None,
            "error_category": "config",
            "error_message": "gitlab requires config_json.project_id for live telemetry",
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
