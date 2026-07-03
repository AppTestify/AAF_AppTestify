"""PM observability — error rate from telemetry."""

from __future__ import annotations

from datetime import datetime, timezone

from agents.schemas import ToolResult
from tools.context import ToolContext, cached_tool


@cached_tool("check_error_rate")
async def check_error_rate(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    try:
        from app.services.observability import snapshot

        obs = snapshot()
        rate = float(obs.get("error_rate", 0.01))
    except Exception:
        rate = 0.01
    signal = min(1.0, rate * 10)
    return ToolResult(
        tool_name="check_error_rate",
        signal=signal,
        captured_at=now,
        evidence_lines=[f"Platform error rate is {rate * 100:.2f}%"],
        raw_signals={"error_rate": rate},
    )
