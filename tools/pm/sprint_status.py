"""JIRA sprint reader — sprint_done_pct, days remaining, stories remaining."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.pm._sprint_data import load_sprint_issues, story_points


def _days_remaining(sprint: dict[str, Any]) -> int:
    end = sprint.get("endDate")
    if not end:
        return 7
    try:
        end_dt = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        delta = (end_dt - datetime.now(timezone.utc)).days
        return max(0, delta)
    except ValueError:
        return 7


async def _direct_get_sprint_status(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    sprint, issues = await load_sprint_issues(ctx)

    total_pts = sum(story_points(i) for i in issues)
    done_pts = sum(
        story_points(i)
        for i in issues
        if str((i.get("fields") or {}).get("status", {}).get("name", "")).lower() in {"done", "closed"}
    )
    sprint_done_pct = round((done_pts / max(1.0, total_pts)) * 100.0, 1)
    stories_remaining = sum(
        1
        for i in issues
        if str((i.get("fields") or {}).get("status", {}).get("name", "")).lower() not in {"done", "closed"}
    )
    days_remaining = _days_remaining(sprint)

    raw: dict[str, Any] = {
        "sprint_done_pct": sprint_done_pct,
        "days_remaining": days_remaining,
        "stories_remaining": stories_remaining,
        "sprint_name": sprint.get("name"),
    }

    pace_risk = 0.0
    if days_remaining > 0 and stories_remaining > days_remaining:
        pace_risk = 0.3
    risk = min(1.0, (100 - sprint_done_pct) / 100.0 * 0.5 + pace_risk)

    lines = [
        f"Sprint completion: {sprint_done_pct:.1f}%",
        f"Days remaining: {days_remaining}",
        f"Stories remaining: {stories_remaining}",
    ]

    return ToolResult(
        tool_name="get_sprint_status",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )


async def get_sprint_status(ctx: ToolContext) -> ToolResult:
    from tools.mcp.router import run_with_transport

    return await run_with_transport(
        ctx,
        agileops_tool="get_sprint_status",
        mcp_tool="get_active_sprint",
        direct_fn=_direct_get_sprint_status,
    )
