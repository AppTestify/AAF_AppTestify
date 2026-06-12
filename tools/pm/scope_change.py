"""Mid-sprint scope change vs sprint start snapshot."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.pm._sprint_data import load_sprint_issues
from tools.sim_data import load_tools_fixture


def _story_points(issue: dict[str, Any]) -> float:
    fields = issue.get("fields") or {}
    for key in ("customfield_10016", "storyPoints"):
        val = fields.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    return 1.0


async def get_scope_change(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    raw: dict[str, Any] = {
        "stories_added_after_start": 0,
        "points_added_after_start": 0.0,
        "scope_change_pct": 0.0,
    }

    sprint_meta, issues = await load_sprint_issues(ctx)
    sprint_id = str(sprint_meta.get("id") or sprint_meta.get("sprint_id") or "active")

    if ctx.sim_mode:
        baseline = load_tools_fixture(ctx.fixtures_dir, "pm_scope_baseline")
        start_keys = set(baseline.get("story_keys") or [])
        start_points = float(baseline.get("committed_points") or 38)
    else:
        snapshots = ctx.extra.get("sprint_snapshots") if isinstance(ctx.extra.get("sprint_snapshots"), dict) else {}
        snap = snapshots.get(sprint_id) if isinstance(snapshots, dict) else None
        if isinstance(snap, dict):
            start_keys = set(snap.get("story_keys") or [])
            start_points = float(snap.get("committed_points") or 0)
        else:
            start_keys = {str(i.get("key")) for i in issues if i.get("key")}
            start_points = sum(_story_points(i) for i in issues)

    current_keys = {str(i.get("key")) for i in issues if i.get("key")}
    added_keys = current_keys - start_keys
    raw["stories_added_after_start"] = len(added_keys)
    raw["points_added_after_start"] = round(
        sum(_story_points(i) for i in issues if str(i.get("key")) in added_keys),
        1,
    )
    if start_points > 0:
        raw["scope_change_pct"] = round((raw["points_added_after_start"] / start_points) * 100.0, 1)

    risk = min(1.0, max(0.05, raw["scope_change_pct"] / 50.0))

    lines = [
        f"Stories added mid-sprint: {raw['stories_added_after_start']}",
        f"Scope change: {raw['scope_change_pct']}% ({raw['points_added_after_start']} points added)",
    ]

    return ToolResult(
        tool_name="get_scope_change",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
