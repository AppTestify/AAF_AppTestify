"""Live AWS telemetry for FinOps integration signals."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from tools.aws_client import get_aws_client
from tools.context import ToolContext


def fetch_aws_signal(
    *,
    region: str = "us-east-1",
    access_key_id: Optional[str] = None,
    secret_access_key: Optional[str] = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    ctx = ToolContext(
        settings=__import__("aaf.config", fromlist=["get_settings"]).get_settings(),
        aws_region=region,
        aws_access_key_id=access_key_id or "",
        aws_secret_access_key=secret_access_key or "",
    )
    ctx.settings.connector_mode = __import__("aaf.config", fromlist=["ConnectorMode"]).ConnectorMode.LIVE

    ce = get_aws_client(ctx, "ce")
    if ce is None:
        return {
            "connector": "aws",
            "mode": "live",
            "enabled": True,
            "freshness": "degraded",
            "cost_trend": "unknown",
            "error_message": "AWS Cost Explorer client unavailable",
            "captured_at": now,
        }

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=7)
    try:
        resp = ce.get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
        )
        amounts = []
        for row in resp.get("ResultsByTime") or []:
            val = float((row.get("Total") or {}).get("UnblendedCost", {}).get("Amount") or 0)
            amounts.append(val)
        trend = "stable"
        if len(amounts) >= 2:
            first = sum(amounts[: len(amounts) // 2]) / max(1, len(amounts) // 2)
            second = sum(amounts[len(amounts) // 2 :]) / max(1, len(amounts) - len(amounts) // 2)
            if second > first * 1.1:
                trend = "up"
            elif second < first * 0.9:
                trend = "down"
        return {
            "connector": "aws",
            "mode": "live",
            "enabled": True,
            "freshness": "fresh",
            "cost_trend": trend,
            "daily_spend_avg": round(sum(amounts) / max(1, len(amounts)), 2),
            "security_findings": 0,
            "captured_at": now,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "connector": "aws",
            "mode": "live",
            "enabled": True,
            "freshness": "degraded",
            "cost_trend": "unknown",
            "error_message": str(exc),
            "captured_at": now,
        }
