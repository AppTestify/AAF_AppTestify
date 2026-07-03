"""AWS cost forecast vs budget."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext, cached_tool
from tools.finops._aws_data import load_finops_bundle
from tools.sim_data import load_tools_fixture


@cached_tool("get_cost_forecast")
async def get_cost_forecast(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    raw: dict[str, Any] = {
        "forecast_spend_usd": 0.0,
        "confidence_interval": {"lower": 0.0, "upper": 0.0},
        "forecast_vs_budget_delta": 0.0,
    }

    if ctx.sim_mode:
        data = load_tools_fixture(ctx.fixtures_dir, "finops_cost_forecast")
        raw.update({k: data.get(k, raw[k]) for k in raw if k in data})
    else:
        from tools.aws_client import get_aws_client

        ce = get_aws_client(ctx, "ce")
        bundle = await load_finops_bundle(ctx)
        budget_pct = float(bundle.get("budget_pct_used") or 0)
        if ce is not None:
            try:
                start = now.date()
                end = start + timedelta(days=30)
                resp = ce.get_cost_forecast(
                    TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
                    Metric="UNBLENDED_COST",
                    Granularity="MONTHLY",
                )
                total = float((resp.get("Total") or {}).get("Amount") or 0)
                raw["forecast_spend_usd"] = round(total, 2)
                for row in resp.get("ForecastResultsByTime") or []:
                    mean = float((row.get("MeanValue") or "0"))
                    if mean:
                        raw["forecast_spend_usd"] = round(mean, 2)
                        break
            except Exception:
                pass
        if budget_pct > 0 and raw["forecast_spend_usd"] > 0:
            implied_budget = raw["forecast_spend_usd"] / max(0.01, budget_pct / 100.0)
            raw["forecast_vs_budget_delta"] = round(raw["forecast_spend_usd"] - implied_budget, 2)

    delta = float(raw["forecast_vs_budget_delta"])
    risk = min(1.0, max(0.05, abs(delta) / 5000.0)) if delta else 0.1

    lines = [
        f"Forecast spend (30d): ${raw['forecast_spend_usd']:.2f}",
        f"Forecast vs budget delta: ${delta:.2f}",
    ]

    return ToolResult(
        tool_name="get_cost_forecast",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
