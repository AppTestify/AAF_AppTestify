"""Rollback detector — inactive-after-active deployment pattern."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.github_client import github_get
from tools.sim_data import load_tools_fixture


async def detect_rollbacks(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    raw: dict[str, Any] = {
        "rollback_24h": 0,
        "rollback_7d": 0,
        "affected_svcs": [],
        "hrs_since_stable": 0.0,
    }

    statuses: list[dict[str, Any]] = []
    if ctx.sim_mode:
        data = load_tools_fixture(ctx.fixtures_dir, "devops_deployments")
        for dep in data.get("deployments") or []:
            for st in dep.get("statuses") or []:
                statuses.append({**st, "environment": dep.get("environment")})
    else:
        dep_data = await github_get(ctx, "/deployments", params={"per_page": 20})
        if isinstance(dep_data, list):
            for dep in dep_data[:10]:
                dep_id = dep.get("id")
                if not dep_id:
                    continue
                st_list = await github_get(ctx, f"/deployments/{dep_id}/statuses")
                if isinstance(st_list, list):
                    for st in st_list:
                        statuses.append({**st, "environment": dep.get("environment")})

    def _parse(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    rollbacks_24h = 0
    rollbacks_7d = 0
    affected: list[str] = []
    last_stable: datetime | None = None

    sorted_statuses = sorted(
        statuses,
        key=lambda s: _parse(s.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc),
    )
    prev_state = None
    for st in sorted_statuses:
        state = str(st.get("state") or "").lower()
        created = _parse(st.get("created_at"))
        if prev_state == "active" and state == "inactive":
            if created and created >= now - timedelta(hours=24):
                rollbacks_24h += 1
            if created and created >= now - timedelta(days=7):
                rollbacks_7d += 1
            env = str(st.get("environment") or "unknown")
            if env not in affected:
                affected.append(env)
        if state == "active" and created:
            last_stable = created
        prev_state = state

    hrs_since_stable = 0.0
    if last_stable:
        hrs_since_stable = round((now - last_stable).total_seconds() / 3600.0, 2)

    raw.update({
        "rollback_24h": rollbacks_24h,
        "rollback_7d": rollbacks_7d,
        "affected_svcs": affected,
        "hrs_since_stable": hrs_since_stable,
    })

    risk = min(1.0, rollbacks_24h * 0.35 + rollbacks_7d * 0.15 + (0.3 if hrs_since_stable > 48 else 0))

    lines = [
        f"Rollbacks (24h): {rollbacks_24h}",
        f"Rollbacks (7d): {rollbacks_7d}",
    ]
    if affected:
        lines.append(f"Affected services: {', '.join(affected)}")
    if hrs_since_stable:
        lines.append(f"Hours since last stable deploy: {hrs_since_stable:.1f}")

    return ToolResult(
        tool_name="detect_rollbacks",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
