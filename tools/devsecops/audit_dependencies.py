"""Dependency audit — vuln distribution by severity."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.devsecops._security_data import load_security_bundle


async def audit_dependencies(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    bundle = await load_security_bundle(ctx)
    deps = bundle.get("dependencies") or {}

    raw: dict[str, Any] = {
        "critical": int(deps.get("critical", 0)),
        "high": int(deps.get("high", 0)),
        "medium": int(deps.get("medium", 0)),
        "low": int(deps.get("low", 0)),
    }

    risk = min(1.0, raw["critical"] * 0.3 + raw["high"] * 0.1 + raw["medium"] * 0.03)

    lines = [
        f"Dependency vulns — critical: {raw['critical']}, high: {raw['high']}, "
        f"medium: {raw['medium']}, low: {raw['low']}",
    ]

    return ToolResult(
        tool_name="audit_dependencies",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
