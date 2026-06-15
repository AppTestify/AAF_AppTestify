"""Velocity risk — committed vs completed story points."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext, cached_tool
from tools.pm._sprint_data import load_sprint_issues, story_points


@cached_tool("calc_velocity_risk")
async def calc_velocity_risk(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    sprint, issues = await load_sprint_issues(ctx)

    committed = sum(story_points(i) for i in issues)
    completed = sum(
        story_points(i)
        for i in issues
        if str((i.get("fields") or {}).get("status", {}).get("name", "")).lower() in {"done", "closed"}
    )
    velocity_ratio = round(completed / max(1.0, committed), 4)
    pace_flag = velocity_ratio < 0.7

    raw: dict[str, Any] = {
        "velocity_ratio": velocity_ratio,
        "pace_flag": pace_flag,
        "committed_points": committed,
        "completed_points": completed,
    }

    risk = 0.1
    if pace_flag:
        risk = min(1.0, 0.5 + (0.7 - velocity_ratio))

    lines = [
        f"Velocity ratio: {velocity_ratio:.2f}",
        f"Pace at risk (<0.7): {'yes' if pace_flag else 'no'}",
    ]

    return ToolResult(
        tool_name="calc_velocity_risk",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
