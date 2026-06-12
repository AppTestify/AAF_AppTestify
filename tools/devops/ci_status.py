"""GitHub Actions reader — ci_pass_rate, failed_steps, blocking_check."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.github_client import github_get
from tools.sim_data import load_github_fixture


def _classify_step(name: str) -> str:
    n = name.lower()
    for label in ("lint", "test", "build", "deploy"):
        if label in n:
            return label
    return "other"


def _parse_run_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def _direct_get_ci_status(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=24)
    raw: dict[str, Any] = {
        "ci_pass_rate": 1.0,
        "failed_steps": [],
        "blocking_check": False,
    }

    if ctx.sim_mode:
        data = load_github_fixture(ctx.fixtures_dir)
        runs = data.get("workflow_runs") or []
    else:
        runs_data = await github_get(ctx, "/actions/runs", params={"per_page": 30})
        runs = (runs_data or {}).get("workflow_runs") or []

    recent = []
    for run in runs:
        created = _parse_run_time(run.get("created_at"))
        if created and created >= window_start:
            recent.append(run)
    if not recent:
        recent = runs[:5]

    total = max(1, len(recent))
    success = sum(1 for r in recent if r.get("conclusion") == "success")
    failed = [r for r in recent if r.get("conclusion") == "failure"]
    ci_pass_rate = round(success / total, 4)
    failed_steps: list[str] = []

    for run in failed[:5]:
        step = _classify_step(str(run.get("name") or "unknown"))
        if step not in failed_steps:
            failed_steps.append(step)

    if not ctx.sim_mode and failed:
        run_id = failed[0].get("id")
        if run_id:
            jobs = await github_get(ctx, f"/actions/runs/{run_id}/jobs")
            for job in (jobs or {}).get("jobs") or []:
                if job.get("conclusion") == "failure":
                    for step in job.get("steps") or []:
                        if step.get("conclusion") == "failure":
                            label = _classify_step(str(step.get("name") or ""))
                            if label not in failed_steps:
                                failed_steps.append(label)

    blocking_check = len(failed) > 0
    risk = 1.0 - ci_pass_rate
    if blocking_check:
        risk = min(1.0, risk + 0.15)

    raw.update({
        "ci_pass_rate": ci_pass_rate,
        "failed_steps": failed_steps,
        "blocking_check": blocking_check,
        "runs_in_window": len(recent),
    })

    lines = [
        f"CI pass rate (24h): {ci_pass_rate * 100:.1f}%",
    ]
    if failed_steps:
        lines.append(f"Failing steps: {', '.join(failed_steps)}")
    if blocking_check:
        lines.append("Blocking CI check: yes")

    return ToolResult(
        tool_name="get_ci_status",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )


async def get_ci_status(ctx: ToolContext) -> ToolResult:
    from tools.context import get_cached_tool_result

    cached = get_cached_tool_result(ctx, "get_ci_status")
    if cached is not None:
        return cached

    from tools.mcp.router import run_with_transport

    return await run_with_transport(
        ctx,
        agileops_tool="get_ci_status",
        mcp_tool="list_workflow_runs",
        direct_fn=_direct_get_ci_status,
    )
