"""Open defects — High/Critical bugs in active sprint."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.pm._sprint_data import load_sprint_issues


def _is_high_critical_bug(issue: dict[str, Any]) -> bool:
    fields = issue.get("fields") or {}
    itype = str(fields.get("issuetype", {}).get("name", "")).lower()
    priority = str(fields.get("priority", {}).get("name", "")).lower()
    status = str(fields.get("status", {}).get("name", "")).lower()
    if itype != "bug" or status in {"done", "closed"}:
        return False
    return priority in {"high", "critical", "highest"}


def _issue_age_days(issue: dict[str, Any]) -> float:
    created = (issue.get("fields") or {}).get("created")
    if not created:
        return 0.0
    try:
        created_dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - created_dt).total_seconds() / 86400.0
    except ValueError:
        return 0.0


async def get_open_defects(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    _, issues = await load_sprint_issues(ctx)

    defects = [i for i in issues if _is_high_critical_bug(i)]
    ages = [_issue_age_days(i) for i in defects]
    oldest_age = max(ages) if ages else 0.0

    raw: dict[str, Any] = {
        "open_bugs_high": len(defects),
        "oldest_defect_age_days": round(oldest_age, 1),
        "defect_keys": [str(i.get("key", "")) for i in defects],
    }

    risk = min(1.0, len(defects) * 0.2 + (0.2 if oldest_age > 14 else 0))

    lines = [f"High/Critical open bugs: {len(defects)}"]
    if oldest_age:
        lines.append(f"Oldest defect age: {oldest_age:.1f} days")

    return ToolResult(
        tool_name="get_open_defects",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
