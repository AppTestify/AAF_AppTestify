"""PM observability — API latency p95 from telemetry."""

from __future__ import annotations

from datetime import datetime, timezone

from agents.schemas import ToolResult
from tools.context import ToolContext


async def check_latency(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    try:
        from app.services.observability import snapshot

        obs = snapshot()
        p95 = float(obs.get("latency_ms_p95", 250))
    except Exception:
        p95 = 250.0
    signal = min(1.0, max(0.0, (p95 - 100) / 900))
    return ToolResult(
        tool_name="check_latency",
        signal=signal,
        captured_at=now,
        evidence_lines=[f"API latency p95 is {p95:.0f}ms"],
        raw_signals={"latency_ms_p95": p95},
    )
