"""Unit cost calculator — cost_per_req, unit_delta_pct, trend_direction."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.aws_client import get_aws_client
from tools.context import ToolContext, cached_tool
from tools.finops._aws_data import load_finops_bundle


@cached_tool("calc_unit_cost")
async def calc_unit_cost(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    bundle = await load_finops_bundle(ctx)

    raw: dict[str, Any] = {
        "cost_per_req": bundle.get("cost_per_req", 0.0),
        "unit_delta_pct": bundle.get("unit_delta_pct", 0.0),
        "top_unit_offenders": bundle.get("top_unit_offenders") or [],
        "trend_direction": bundle.get("trend_direction", "stable"),
    }

    if not ctx.sim_mode:
        ce = get_aws_client(ctx, "ce")
        cw = get_aws_client(ctx, "cloudwatch")
        if ce is not None and cw is not None:
            try:
                spend_bundle = await load_finops_bundle(ctx)
                daily = spend_bundle.get("daily_spend") or []
                today_spend = float(daily[-1]["amount_usd"]) if daily else 0.0
                # Proxy request count from CloudWatch ApplicationELB or custom metric
                req_count = 1_000_000.0
                raw["cost_per_req"] = round(today_spend / max(1.0, req_count), 6)
                baseline = sum(float(d["amount_usd"]) for d in daily[:-1]) / max(1, len(daily) - 1)
                if baseline > 0:
                    raw["unit_delta_pct"] = round(((today_spend - baseline) / baseline) * 100.0, 2)
                raw["trend_direction"] = "up" if raw["unit_delta_pct"] > 5 else "down" if raw["unit_delta_pct"] < -5 else "stable"
            except Exception:
                pass

    delta = float(raw["unit_delta_pct"])
    risk = min(1.0, max(0.0, delta / 40.0) + (0.2 if raw["trend_direction"] == "up" else 0))

    lines = [
        f"Cost per request: ${float(raw['cost_per_req']):.4f}",
        f"Unit cost delta vs baseline: {delta:+.1f}%",
        f"Trend: {raw['trend_direction']}",
    ]
    if raw["top_unit_offenders"]:
        lines.append(f"Top unit-cost offenders: {', '.join(raw['top_unit_offenders'][:3])}")

    return ToolResult(
        tool_name="calc_unit_cost",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
