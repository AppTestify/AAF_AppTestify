"""Team capacity — sprint availability vs planned load."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.sim_data import load_tools_fixture


def _capacity_prefs(ctx: ToolContext) -> dict[str, Any]:
    prefs = ctx.extra.get("ui_preferences") if isinstance(ctx.extra.get("ui_preferences"), dict) else {}
    cap = prefs.get("team_capacity") or ctx.extra.get("team_capacity") or {}
    return cap if isinstance(cap, dict) else {}


async def get_team_capacity(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    raw: dict[str, Any] = {
        "team_capacity_pct": 100.0,
        "planned_vs_available_hours": 0.0,
        "leave_count_this_sprint": 0,
    }

    if ctx.sim_mode:
        data = load_tools_fixture(ctx.fixtures_dir, "pm_team_capacity")
        raw.update({k: data.get(k, raw[k]) for k in raw})
    else:
        cap = _capacity_prefs(ctx)
        available = float(cap.get("available_hours") or cap.get("available") or 0)
        planned = float(cap.get("planned_hours") or cap.get("planned") or 0)
        raw["leave_count_this_sprint"] = int(cap.get("leave_count") or 0)
        if available > 0:
            raw["team_capacity_pct"] = round(min(100.0, (planned / available) * 100.0), 1)
            raw["planned_vs_available_hours"] = round(planned - available, 1)

    pct = float(raw["team_capacity_pct"])
    risk = 0.05
    if pct > 100:
        risk = min(1.0, 0.5 + (pct - 100) / 50.0)
    elif raw["leave_count_this_sprint"] >= 3:
        risk = min(1.0, 0.4 + raw["leave_count_this_sprint"] * 0.1)

    lines = [
        f"Team capacity: {pct}%",
        f"Planned vs available hours: {raw['planned_vs_available_hours']}",
        f"Leave count this sprint: {raw['leave_count_this_sprint']}",
    ]

    return ToolResult(
        tool_name="get_team_capacity",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
