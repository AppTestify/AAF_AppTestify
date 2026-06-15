"""Policy violations — OPA/Checkov/CSPM style counts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext, cached_tool
from tools.devsecops._security_data import load_security_bundle


@cached_tool("check_policy_violations")
async def check_policy_violations(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    bundle = await load_security_bundle(ctx)

    raw: dict[str, Any] = {
        "violation_count": int(bundle.get("policy_violations", 0)),
        "violated_rules": list(bundle.get("violated_rules") or [])[:10],
    }

    risk = min(1.0, raw["violation_count"] * 0.2)

    lines = [f"Policy violations: {raw['violation_count']}"]
    if raw["violated_rules"]:
        lines.append(f"Violated rules: {', '.join(raw['violated_rules'][:3])}")

    return ToolResult(
        tool_name="check_policy_violations",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
