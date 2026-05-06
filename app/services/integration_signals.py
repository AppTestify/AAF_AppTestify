"""Synthetic cloud integration signal fetchers for Azure/AWS/GitHub/Jira."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.config import TenantConnectorConfig
from app.security import decrypt_json
from app.services.github_live import fetch_github_signal
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

    if name == "azure":
        return {
            "connector": "azure",
            "enabled": True,
            "freshness": "fresh",
            "latency_ms": 420,
            "errors_24h": 0,
            "cost_trend": "stable",
            "policy_violations": 1,
            "deployment_health": "green",
            "captured_at": now,
        }
    if name == "aws":
        return {
            "connector": "aws",
            "enabled": True,
            "freshness": "fresh",
            "latency_ms": 390,
            "errors_24h": 0,
            "cost_trend": "up_4pct",
            "security_findings": 2,
            "release_readiness": "warning",
            "captured_at": now,
        }
    if name == "github":
        cfg = connector.config_json or {}
        if cfg.get("repo"):
            try:
                creds = decrypt_json(connector.encrypted_credentials_json, secret=get_settings().app_encryption_key)
                token = creds.get("token") if isinstance(creds, dict) else None
                return fetch_github_signal(str(cfg["repo"]), token=token)
            except Exception:  # noqa: BLE001
                # fallback to synthetic data to keep the run non-blocking
                pass
        return {
            "connector": "github",
            "enabled": True,
            "mode": "synthetic",
            "freshness": "fresh",
            "latency_ms": 180,
            "errors_24h": 0,
            "open_prs": 14,
            "failing_checks": 1,
            "captured_at": now,
        }
    if name == "jira":
        return {
            "connector": "jira",
            "enabled": True,
            "freshness": "fresh",
            "latency_ms": 210,
            "errors_24h": 0,
            "blocked_tickets": 3,
            "lead_time_days": 4.7,
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
