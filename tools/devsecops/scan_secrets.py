"""Secret scanning — secrets_detected, affected files."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.devsecops._security_data import load_security_bundle


async def scan_secrets(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    bundle = await load_security_bundle(ctx)

    raw: dict[str, Any] = {
        "secrets_detected": bool(bundle.get("secrets_detected")),
        "affected_files": list(bundle.get("secret_files") or [])[:10],
    }

    risk = 1.0 if raw["secrets_detected"] else 0.0

    lines = [
        f"Secrets detected: {'yes' if raw['secrets_detected'] else 'no'}",
    ]
    if raw["affected_files"]:
        lines.append(f"Affected locations: {len(raw['affected_files'])}")

    return ToolResult(
        tool_name="scan_secrets",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
