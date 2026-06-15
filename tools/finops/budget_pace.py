"""Budget tracker — budget_pct_used, pace_ratio, forecast_overage, alert_triggered."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.aws_client import get_aws_client
from tools.context import ToolContext, cached_tool
from tools.finops._aws_data import load_finops_bundle


@cached_tool("check_budget_pace")
async def check_budget_pace(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    bundle = await load_finops_bundle(ctx)

    raw: dict[str, Any] = {
        "budget_pct_used": bundle.get("budget_pct_used", 0.0),
        "days_elapsed_pct": bundle.get("days_elapsed_pct", 0.0),
        "pace_ratio": bundle.get("pace_ratio", 1.0),
        "forecast_overage": bool(bundle.get("forecast_overage")),
        "alert_triggered": bool(bundle.get("alert_triggered")),
    }

    if not ctx.sim_mode:
        budgets = get_aws_client(ctx, "budgets")
        if budgets is not None:
            try:
                resp = budgets.describe_budgets()
                for b in resp.get("Budgets") or []:
                    budget_val = float(b.get("BudgetLimit", {}).get("Amount") or 0)
                    actual = float((b.get("CalculatedSpend") or {}).get("ActualSpend", {}).get("Amount") or 0)
                    if budget_val > 0:
                        raw["budget_pct_used"] = round((actual / budget_val) * 100.0, 2)
                    raw["alert_triggered"] = bool(b.get("BudgetLimit"))
            except Exception:
                pass

    pace = float(raw["pace_ratio"])
    risk = min(1.0, max(0.0, (pace - 1.0) * 0.4 + float(raw["budget_pct_used"]) / 200.0))
    if raw["forecast_overage"]:
        risk = min(1.0, risk + 0.25)

    lines = [
        f"Budget consumed: {raw['budget_pct_used']:.1f}%",
        f"Burn pace ratio: {pace:.2f}",
    ]
    if raw["forecast_overage"]:
        lines.append("Forecasted month-end spend exceeds budget")
    if raw["alert_triggered"]:
        lines.append("Budget alert threshold triggered")

    return ToolResult(
        tool_name="check_budget_pace",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
