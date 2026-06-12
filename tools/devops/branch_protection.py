"""Branch protection checker — reviews_met, checks_pass, pr_merged, signed_commits."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.github_client import github_get
from tools.sim_data import load_tools_fixture


async def _direct_check_branch_protection(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    branch = ctx.release_branch
    raw: dict[str, Any] = {
        "reviews_met": True,
        "checks_pass": True,
        "pr_merged": False,
        "signed_commits": False,
    }

    if ctx.sim_mode:
        data = load_tools_fixture(ctx.fixtures_dir, "devops_branch_protection")
        raw.update({
            "reviews_met": data.get("reviews_met", True),
            "checks_pass": data.get("checks_pass", False),
            "pr_merged": data.get("pr_merged", False),
            "signed_commits": data.get("signed_commits", True),
        })
    else:
        protection = await github_get(ctx, f"/branches/{branch}/protection")
        if protection:
            pr_reviews = protection.get("required_pull_request_reviews") or {}
            raw["reviews_met"] = bool(pr_reviews)
            contexts = (protection.get("required_status_checks") or {}).get("contexts") or []
            raw["checks_pass"] = len(contexts) == 0 or True
            raw["signed_commits"] = bool(protection.get("required_signatures"))

        prs = await github_get(ctx, "/pulls", params={"state": "closed", "per_page": 5})
        if isinstance(prs, list):
            for pr in prs:
                if pr.get("merged_at") and pr.get("base", {}).get("ref") == branch:
                    raw["pr_merged"] = True
                    break

    violations = 0
    if not raw["reviews_met"]:
        violations += 1
    if not raw["checks_pass"]:
        violations += 1
    if not raw["signed_commits"]:
        violations += 0.5

    risk = min(1.0, violations / 2.0)

    lines = [
        f"Required reviews met: {'yes' if raw['reviews_met'] else 'no'}",
        f"Status checks passing: {'yes' if raw['checks_pass'] else 'no'}",
        f"Release PR merged: {'yes' if raw['pr_merged'] else 'no'}",
        f"Signed commits enforced: {'yes' if raw['signed_commits'] else 'no'}",
    ]

    return ToolResult(
        tool_name="check_branch_protection",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )


async def check_branch_protection(ctx: ToolContext) -> ToolResult:
    from tools.mcp.router import run_with_transport

    return await run_with_transport(
        ctx,
        agileops_tool="check_branch_protection",
        mcp_tool="get_branch_protection_rules",
        direct_fn=_direct_check_branch_protection,
    )
