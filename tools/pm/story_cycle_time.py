"""Jira story cycle time from changelog."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.jira_client import jira_get
from tools.pm._sprint_data import load_sprint_issues
from tools.sim_data import load_tools_fixture


def _cycle_days_from_changelog(changelog: dict[str, Any]) -> float | None:
    histories = changelog.get("histories") or []
    in_progress: datetime | None = None
    done: datetime | None = None
    for h in histories:
        created = h.get("created")
        if not created:
            continue
        try:
            ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError:
            continue
        for item in h.get("items") or []:
            field = str(item.get("field") or "").lower()
            to_str = str(item.get("toString") or "").lower()
            if field == "status" and "progress" in to_str:
                in_progress = ts
            if field == "status" and to_str in ("done", "closed", "resolved"):
                done = ts
    if in_progress and done and done > in_progress:
        return (done - in_progress).total_seconds() / 86400.0
    return None


async def get_story_cycle_time(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    raw: dict[str, Any] = {
        "avg_cycle_time_days": 0.0,
        "cycle_time_trend": "stable",
        "stories_stuck_in_review": 0,
        "longest_cycle_time_story": "",
    }

    if ctx.sim_mode:
        data = load_tools_fixture(ctx.fixtures_dir, "pm_story_cycle_time")
        raw.update({k: data.get(k, raw[k]) for k in raw})
    else:
        _, issues = await load_sprint_issues(ctx)
        cycles: list[float] = []
        longest = 0.0
        longest_key = ""
        stuck = 0
        for issue in issues[:20]:
            key = issue.get("key")
            if not key:
                continue
            fields = issue.get("fields") or {}
            status = str((fields.get("status") or {}).get("name") or "").lower()
            if "review" in status:
                stuck += 1
            cl = await jira_get(ctx, f"/rest/api/3/issue/{key}/changelog")
            if isinstance(cl, dict):
                days = _cycle_days_from_changelog(cl)
                if days is not None:
                    cycles.append(days)
                    if days > longest:
                        longest = days
                        longest_key = str(key)
        if cycles:
            raw["avg_cycle_time_days"] = round(sum(cycles) / len(cycles), 2)
            raw["longest_cycle_time_story"] = longest_key
            raw["stories_stuck_in_review"] = stuck
            if raw["avg_cycle_time_days"] > 4.0:
                raw["cycle_time_trend"] = "degrading"
            elif raw["avg_cycle_time_days"] < 2.5:
                raw["cycle_time_trend"] = "improving"

    risk = min(1.0, max(0.05, raw["avg_cycle_time_days"] / 8.0))
    if raw["stories_stuck_in_review"] >= 3:
        risk = min(1.0, risk + 0.2)

    lines = [
        f"Avg cycle time: {raw['avg_cycle_time_days']} days ({raw['cycle_time_trend']})",
        f"Stories stuck in review (3+ days context): {raw['stories_stuck_in_review']}",
    ]

    return ToolResult(
        tool_name="get_story_cycle_time",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
