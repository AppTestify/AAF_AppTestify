"""Weighted confidence scoring with staleness penalties."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.schemas import ToolResult


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def apply_staleness_penalty(
    signal: float,
    captured_at: datetime,
    *,
    staleness_hours: float,
    penalty_factor: float,
) -> float:
    """Down-weight signals older than the staleness window."""
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)
    age_hours = (_utc_now() - captured_at).total_seconds() / 3600.0
    if age_hours > staleness_hours:
        return signal * penalty_factor
    return signal


class ConfidenceScorer:
    """Compute agent confidence as weighted sum of tool risk signals."""

    @staticmethod
    def compute(
        tool_results: list[ToolResult],
        weights: dict[str, float],
        *,
        staleness_hours: float = 4.0,
        penalty_factor: float = 0.5,
        correlation_boost: float | None = None,
    ) -> float:
        total_weight = sum(weights.values()) or 1.0
        score = 0.0
        by_name = {r.tool_name: r for r in tool_results}
        for name, weight in weights.items():
            result = by_name.get(name)
            if result is None:
                continue
            adjusted = apply_staleness_penalty(
                result.signal,
                result.captured_at,
                staleness_hours=staleness_hours,
                penalty_factor=penalty_factor,
            )
            score += (weight / total_weight) * adjusted
        if correlation_boost is not None and correlation_boost > 0:
            score = min(1.0, score * (1.0 + correlation_boost))
        return round(max(0.0, min(1.0, score)), 4)

    @staticmethod
    def is_stale(
        captured_at: datetime,
        *,
        staleness_hours: float,
    ) -> bool:
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=timezone.utc)
        age_hours = (_utc_now() - captured_at).total_seconds() / 3600.0
        return age_hours > staleness_hours
