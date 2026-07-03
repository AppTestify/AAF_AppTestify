"""GitHub Actions workflow config and freeze window checks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext, cached_tool
from tools.github_client import github_get
from tools.sim_data import load_tools_fixture


@cached_tool("check_pipeline_config")
async def check_pipeline_config(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    prefs = ctx.extra.get("ui_preferences") if isinstance(ctx.extra.get("ui_preferences"), dict) else {}
    freeze = prefs.get("freeze_window") or ctx.extra.get("freeze_window") or {}
    freeze_active = bool(freeze.get("active")) if isinstance(freeze, dict) else False

    raw: dict[str, Any] = {
        "pipeline_has_approval_gate": False,
        "environments_protected": [],
        "manual_gate_configured": False,
        "freeze_window_active": freeze_active,
    }

    if ctx.sim_mode:
        data = load_tools_fixture(ctx.fixtures_dir, "devops_pipeline_config")
        raw.update({k: data.get(k, raw[k]) for k in raw if k in data})
        if "freeze_window_active" in data:
            raw["freeze_window_active"] = bool(data["freeze_window_active"])
    else:
        contents = await github_get(ctx, "/contents/.github/workflows")
        if isinstance(contents, list):
            for item in contents:
                name = str(item.get("name") or "")
                if not name.endswith((".yml", ".yaml")):
                    continue
                path = item.get("path")
                if not path:
                    continue
                # Shallow YAML scan via download URL would need extra fetch; use name heuristics
                if "prod" in name or "release" in name or "deploy" in name:
                    raw["environments_protected"].append(name)
                    raw["pipeline_has_approval_gate"] = True

    risk = 0.05
    if raw["freeze_window_active"] and not raw["manual_gate_configured"]:
        risk = 0.85
    elif raw["freeze_window_active"]:
        risk = 0.45

    lines = [
        f"Freeze window active: {raw['freeze_window_active']}",
        f"Approval gate in pipeline: {raw['pipeline_has_approval_gate']}",
    ]
    if raw["environments_protected"]:
        lines.append(f"Protected workflow files: {', '.join(raw['environments_protected'][:3])}")

    return ToolResult(
        tool_name="check_pipeline_config",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
