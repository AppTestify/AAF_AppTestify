"""Shared sprint data loader for PM tools."""

from __future__ import annotations

from typing import Any

from tools.context import ToolContext
from tools.jira_client import jira_get
from tools.sim_data import load_jira_fixture, load_tools_fixture


async def load_sprint_issues(ctx: ToolContext) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if ctx.sim_mode:
        data = load_tools_fixture(ctx.fixtures_dir, "pm_sprint")
        sprint = data.get("sprint") or {}
        issues = data.get("issues") or []
        if not issues:
            jira = load_jira_fixture(ctx.fixtures_dir)
            issues = jira.get("issues") or []
        return sprint, issues

    board_id = ctx.jira_board_id
    sprints = await jira_get(ctx, f"/rest/agile/1.0/board/{board_id}/sprint", params={"state": "active"})
    values = (sprints or {}).get("values") or []
    sprint = values[0] if values else {}
    sprint_id = sprint.get("id")
    issues: list[dict[str, Any]] = []
    if sprint_id:
        result = await jira_get(ctx, f"/rest/agile/1.0/sprint/{sprint_id}/issue")
        issues = (result or {}).get("issues") or []
    return sprint, issues


def story_points(issue: dict[str, Any]) -> float:
    fields = issue.get("fields") or {}
    for key in ("customfield_10016", "storyPoints", "story_points"):
        val = fields.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    return 1.0
