"""Create a Jira governance blocker issue."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.jira_client import jira_post


async def create_jira_blocker(
    ctx: ToolContext,
    *,
    summary: str,
    description: str,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Create a Jira issue; returns {key, url, simulated}."""
    issue_labels = ["casantris-governance", *(labels or [])]
    if ctx.sim_mode or not ctx.jira_url:
        sim_key = f"SIM-{int(datetime.now(timezone.utc).timestamp()) % 100000}"
        return {
            "key": sim_key,
            "url": f"{ctx.jira_url or 'https://jira.example.com'}/browse/{sim_key}",
            "simulated": True,
            "summary": summary,
        }

    payload = {
        "fields": {
            "project": {"key": ctx.jira_project},
            "summary": summary[:255],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description[:8000]}],
                    }
                ],
            },
            "issuetype": {"name": "Task"},
            "labels": issue_labels,
        }
    }
    result = await jira_post(ctx, "/rest/api/3/issue", payload)
    if not result:
        raise RuntimeError("Jira issue creation failed")
    key = str(result.get("key", ""))
    return {
        "key": key,
        "url": f"{ctx.jira_url.rstrip('/')}/browse/{key}",
        "simulated": False,
        "summary": summary,
    }


async def create_blocker_tool(ctx: ToolContext) -> ToolResult:
    """Tool entrypoint — creates blocker from ctx.extra governance context."""
    now = datetime.now(timezone.utc)
    extra = ctx.extra or {}
    summary = str(extra.get("summary") or "Governance release blocker")
    description = str(extra.get("description") or "Created by Casantris governance automation.")
    try:
        created = await create_jira_blocker(ctx, summary=summary, description=description)
        return ToolResult(
            tool_name="create_blocker",
            signal=0.9,
            captured_at=now,
            raw_signals=created,
            evidence_lines=[f"Jira blocker {created['key']}: {summary}"],
        )
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            tool_name="create_blocker",
            signal=0.0,
            captured_at=now,
            raw_signals={"error": str(exc)},
            evidence_lines=[f"Failed to create Jira blocker: {exc}"],
        )
