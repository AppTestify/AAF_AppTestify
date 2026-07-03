"""FinOps efficiency scorer — Ci score 0-1."""

from __future__ import annotations

from agents.schemas import ToolResult
from tools.scoring import ConfidenceScorer

FINOPS_TOOL_WEIGHTS: dict[str, float] = {
    "get_spend_trend": 0.30,
    "check_budget_pace": 0.25,
    "detect_scaling_anomaly": 0.20,
    "calc_unit_cost": 0.15,
    "get_ri_coverage": 0.10,
}


def compute_ci_score(
    tool_results: list[ToolResult],
    *,
    correlation_boost: float = 0.0,
) -> float:
    """Ci = weighted risk score inverted to efficiency (1 - risk)."""
    risk = ConfidenceScorer.compute(
        tool_results,
        FINOPS_TOOL_WEIGHTS,
        staleness_hours=6.0,
        penalty_factor=0.4,
        correlation_boost=correlation_boost,
    )
    return round(1.0 - risk, 4)


def finops_correlation_boost(tool_results: list[ToolResult]) -> float:
    """Scaling anomaly + spend spike raises confidence."""
    by_name = {r.tool_name: r for r in tool_results}
    scaling = by_name.get("detect_scaling_anomaly")
    spend = by_name.get("get_spend_trend")
    if not scaling or not spend:
        return 0.0
    orphan = bool(scaling.raw_signals.get("orphan_scale_flag"))
    anomaly = bool(spend.raw_signals.get("anomaly_flag"))
    if orphan and anomaly:
        return 0.15
    return 0.0
