"""Map spend patterns to predefined claim templates."""

from __future__ import annotations

from agents.schemas import ToolResult


def generate_cost_claim(tool_results: list[ToolResult]) -> str:
    by_name = {r.tool_name: r for r in tool_results}
    spend = by_name.get("get_spend_trend")
    budget = by_name.get("check_budget_pace")
    scaling = by_name.get("detect_scaling_anomaly")

    if spend and spend.raw_signals.get("anomaly_flag"):
        return "Cloud cost increase detected."
    if budget and budget.raw_signals.get("forecast_overage"):
        return "Budget burn pace exceeds plan — forecasted overage."
    if scaling and scaling.raw_signals.get("orphan_scale_flag"):
        return "Runaway scaling may be driving unexpected cloud spend."
    if spend and float(spend.raw_signals.get("wow_delta_pct", 0)) > 15:
        return "Cloud spend trending upward week-over-week."
    return "No material cost anomalies in evidence."
