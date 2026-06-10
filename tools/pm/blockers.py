"""Blocker counter — sprint=ACTIVE AND status=Blocked."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.pm._sprint_data import load_sprint_issues


def _is_blocked(issue: dict[str, Any]) -> bool:
    fields = issue.get("fields") or {}
    status = str(fields.get("status", {}).get("name", "")).lower()
    summary = str(fields.get("summary", "")).lower()
    return "block" in status or "blocked" in summary


async def count_blockers(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    _, issues = await load_sprint_issues(ctx)

    blocked = [i for i in issues if _is_blocked(i)]
    keys = [str(i.get("key", "")) for i in blocked]
    reasons = [str((i.get("fields") or {}).get("summary", ""))[:80] for i in blocked]

    count = len(blocked)
    raw: dict[str, Any] = {
        "blocked_count": count,
        "story_keys": keys,
        "blocker_reasons": reasons,
    }

    # Spec: each blocker above 0 sharply increases score; 5+ triggers action
    if count >= 5:
        risk = 1.0
    elif count > 0:
        risk = min(1.0, 0.4 + count * 0.12)
    else:
        risk = 0.05

    lines = [f"Blocked stories: {count}"]
    if keys:
        lines.append(f"Blocked keys: {', '.join(keys[:5])}")
    for reason in reasons[:3]:
        lines.append(f"Blocker: {reason}")

    return ToolResult(
        tool_name="count_blockers",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
