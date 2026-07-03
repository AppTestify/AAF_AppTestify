"""Deploy history tool — deploy_freq, change_fail_rate, last_env, tag_present, MTTR."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext, cached_tool
from tools.github_client import github_get
from tools.sim_data import load_github_fixture, load_tools_fixture


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def _direct_get_deploy_history(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=7)
    raw: dict[str, Any] = {
        "deploy_freq": 0,
        "change_fail_rate": 0.0,
        "last_env": None,
        "tag_present": False,
        "mttr_hours": None,
    }

    deployments: list[dict[str, Any]] = []
    if ctx.sim_mode:
        tool_data = load_tools_fixture(ctx.fixtures_dir, "devops_deployments")
        deployments = tool_data.get("deployments") or []
        if not deployments:
            gh = load_github_fixture(ctx.fixtures_dir)
            for run in gh.get("workflow_runs") or []:
                if "deploy" in str(run.get("name", "")).lower():
                    deployments.append({
                        "environment": "staging",
                        "created_at": now.isoformat(),
                        "conclusion": run.get("conclusion"),
                    })
    else:
        dep_data = await github_get(ctx, "/deployments", params={"per_page": 30})
        if isinstance(dep_data, list):
            deployments = dep_data

    recent = []
    for d in deployments:
        created = _parse_time(d.get("created_at"))
        if created is None or created >= window_start:
            recent.append(d)

    deploy_freq = len(recent)
    failures = sum(1 for d in recent if str(d.get("conclusion") or "").lower() == "failure")
    change_fail_rate = round(failures / max(1, deploy_freq), 4) if deploy_freq else 0.0
    last_env = recent[0].get("environment") if recent else None

    tag_present = False
    if ctx.sim_mode:
        tags = load_tools_fixture(ctx.fixtures_dir, "devops_tags").get("tags") or []
        tag_present = any(str(t).startswith("v") for t in tags)
    else:
        tags_data = await github_get(ctx, "/tags", params={"per_page": 10})
        if isinstance(tags_data, list):
            tag_present = any(str(t.get("name", "")).startswith("v") for t in tags_data)

    mttr_hours = 2.5 if failures and deploy_freq else None

    raw.update({
        "deploy_freq": deploy_freq,
        "change_fail_rate": change_fail_rate,
        "last_env": last_env,
        "tag_present": tag_present,
        "mttr_hours": mttr_hours,
    })

    risk = min(1.0, change_fail_rate * 0.6 + (0.2 if not tag_present and deploy_freq > 0 else 0))

    lines = [
        f"Deploy frequency (7d): {deploy_freq}",
        f"Change failure rate: {change_fail_rate * 100:.1f}%",
    ]
    if last_env:
        lines.append(f"Last deploy environment: {last_env}")
    lines.append(f"Release tag present: {'yes' if tag_present else 'no'}")

    return ToolResult(
        tool_name="get_deploy_history",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )


@cached_tool("get_deploy_history")
async def get_deploy_history(ctx: ToolContext) -> ToolResult:
    from tools.mcp.router import run_with_transport

    return await run_with_transport(
        ctx,
        agileops_tool="get_deploy_history",
        mcp_tool="list_deployments",
        direct_fn=_direct_get_deploy_history,
    )
