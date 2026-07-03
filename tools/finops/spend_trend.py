"""AWS Cost Explorer — daily_spend, wow_delta_pct, top_services, anomaly_flag."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext, cached_tool
from tools.finops._aws_data import load_finops_bundle


@cached_tool("get_spend_trend")
async def get_spend_trend(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    bundle = await load_finops_bundle(ctx)

    raw: dict[str, Any] = {
        "daily_spend": bundle.get("daily_spend") or [],
        "wow_delta_pct": bundle.get("wow_delta_pct", 0.0),
        "top_services": bundle.get("top_services") or [],
        "anomaly_flag": bool(bundle.get("anomaly_flag")),
    }

    wow = float(raw["wow_delta_pct"])
    risk = min(1.0, max(0.0, wow / 50.0) + (0.35 if raw["anomaly_flag"] else 0))

    lines = [
        f"Week-over-week spend delta: {wow:+.1f}%",
        f"Top cost drivers: {', '.join(raw['top_services'][:3]) or 'n/a'}",
    ]
    if raw["anomaly_flag"]:
        lines.append("Spend anomaly detected (>30% WoW increase)")

    return ToolResult(
        tool_name="get_spend_trend",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
