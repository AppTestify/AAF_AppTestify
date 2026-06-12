"""AWS cost breakdown by team/service/environment tags."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.sim_data import load_tools_fixture


async def get_cost_by_tag(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    raw: dict[str, Any] = {
        "cost_by_team_tag": [],
        "cost_by_environment": {},
        "untagged_resource_cost": 0.0,
        "top_spending_team": "",
    }

    if ctx.sim_mode:
        data = load_tools_fixture(ctx.fixtures_dir, "finops_cost_by_tag")
        raw.update({k: data.get(k, raw[k]) for k in raw})
    else:
        from tools.aws_client import get_aws_client

        ce = get_aws_client(ctx, "ce")
        if ce is not None:
            try:
                from datetime import timedelta

                end = datetime.now(timezone.utc).date()
                start = end - timedelta(days=30)
                resp = ce.get_cost_and_usage(
                    TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
                    Granularity="MONTHLY",
                    Metrics=["UnblendedCost"],
                    GroupBy=[{"Type": "TAG", "Key": "Team"}],
                )
                teams: list[dict[str, Any]] = []
                for row in resp.get("ResultsByTime") or []:
                    for group in row.get("Groups") or []:
                        key = (group.get("Keys") or ["Untagged"])[0]
                        amt = float((group.get("Metrics") or {}).get("UnblendedCost", {}).get("Amount") or 0)
                        if key in ("Team$", "", "Untagged"):
                            raw["untagged_resource_cost"] += amt
                        else:
                            team = key.replace("Team$", "")
                            teams.append({"team": team, "cost_usd": round(amt, 2)})
                teams.sort(key=lambda x: x["cost_usd"], reverse=True)
                raw["cost_by_team_tag"] = teams
                if teams:
                    raw["top_spending_team"] = teams[0]["team"]
            except Exception:
                pass

    total = sum(t.get("cost_usd", 0) for t in raw["cost_by_team_tag"]) + float(raw["untagged_resource_cost"])
    risk = 0.1
    if raw["untagged_resource_cost"] > 0 and total > 0:
        risk = min(0.7, raw["untagged_resource_cost"] / total)

    lines = [
        f"Top spending team: {raw['top_spending_team'] or 'n/a'}",
        f"Untagged resource cost: ${raw['untagged_resource_cost']:.2f}",
    ]
    for row in (raw["cost_by_team_tag"] or [])[:3]:
        lines.append(f"{row.get('team')}: ${row.get('cost_usd')}")

    return ToolResult(
        tool_name="get_cost_by_tag",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
