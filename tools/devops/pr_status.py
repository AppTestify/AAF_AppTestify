"""GitHub open PR status for release branch."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.github_client import github_get
from tools.sim_data import load_tools_fixture


async def get_pr_status(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    base = ctx.release_branch or "main"
    raw: dict[str, Any] = {
        "open_pr_count": 0,
        "approved_count": 0,
        "changes_requested_count": 0,
        "draft_pr_flag": False,
        "oldest_open_pr_days": 0,
    }

    if ctx.sim_mode:
        data = load_tools_fixture(ctx.fixtures_dir, "devops_pr_status")
        raw.update({k: data.get(k, raw[k]) for k in raw})
    else:
        pulls = await github_get(ctx, "/pulls", params={"state": "open", "base": base, "per_page": 30})
        if isinstance(pulls, list):
            raw["open_pr_count"] = len(pulls)
            oldest_days = 0
            for pr in pulls:
                if pr.get("draft"):
                    raw["draft_pr_flag"] = True
                created = pr.get("created_at")
                if created:
                    try:
                        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        days = (now - dt).days
                        oldest_days = max(oldest_days, days)
                    except ValueError:
                        pass
                pr_num = pr.get("number")
                if pr_num:
                    reviews = await github_get(ctx, f"/pulls/{pr_num}/reviews")
                    if isinstance(reviews, list):
                        states = {str(r.get("state", "")).upper() for r in reviews}
                        if "CHANGES_REQUESTED" in states:
                            raw["changes_requested_count"] += 1
                        elif "APPROVED" in states:
                            raw["approved_count"] += 1
            raw["oldest_open_pr_days"] = oldest_days

    risk = 0.05
    if raw["changes_requested_count"] > 0:
        risk = min(1.0, 0.5 + raw["changes_requested_count"] * 0.15)
    elif raw["open_pr_count"] > 0:
        risk = min(0.7, 0.2 + raw["open_pr_count"] * 0.08)

    lines = [
        f"Open PRs on {base}: {raw['open_pr_count']}",
        f"Approved: {raw['approved_count']}, changes requested: {raw['changes_requested_count']}",
    ]
    if raw["draft_pr_flag"]:
        lines.append("Draft PRs present on release branch")

    return ToolResult(
        tool_name="get_pr_status",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
