"""CVE scanner — critical/high counts, affected packages."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.devsecops._security_data import load_security_bundle


async def _direct_scan_cves(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    bundle = await load_security_bundle(ctx)
    cves = bundle.get("cves") or {}

    raw: dict[str, Any] = {
        "critical_count": int(cves.get("critical", 0)),
        "high_count": int(cves.get("high", 0)),
        "affected_packages": list(cves.get("packages") or [])[:10],
    }

    risk = min(1.0, raw["critical_count"] * 0.5 + raw["high_count"] * 0.15)

    lines = [
        f"Critical CVEs: {raw['critical_count']}",
        f"High CVEs: {raw['high_count']}",
    ]
    if raw["affected_packages"]:
        lines.append(f"Affected packages: {', '.join(raw['affected_packages'][:3])}")

    return ToolResult(
        tool_name="scan_cves",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )


async def scan_cves(ctx: ToolContext) -> ToolResult:
    from tools.mcp.router import run_with_transport

    return await run_with_transport(
        ctx,
        agileops_tool="scan_cves",
        mcp_tool="list_code_scanning_alerts",
        direct_fn=_direct_scan_cves,
    )
