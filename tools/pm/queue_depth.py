"""PM observability — governance run queue depth."""

from __future__ import annotations

from datetime import datetime, timezone

from agents.schemas import ToolResult
from tools.context import ToolContext


async def check_queue_depth(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    try:
        from app.services.observability import snapshot

        obs = snapshot()
        depth = int(obs.get("run_queue_depth", 0))
    except Exception:
        depth = 0
    signal = min(1.0, depth / 10.0)
    return ToolResult(
        tool_name="check_queue_depth",
        signal=signal,
        captured_at=now,
        evidence_lines=[f"Governance run queue depth is {depth}"],
        raw_signals={"run_queue_depth": depth},
    )
