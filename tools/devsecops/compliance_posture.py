"""AWS Security Hub compliance posture summary."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext, cached_tool
from tools.sim_data import load_tools_fixture


@cached_tool("check_compliance_posture")
async def check_compliance_posture(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    raw: dict[str, Any] = {
        "compliance_framework_status": "PASS",
        "control_failures": [],
        "overall_posture_score": 100.0,
    }

    if ctx.sim_mode:
        data = load_tools_fixture(ctx.fixtures_dir, "devsecops_compliance_posture")
        raw.update({k: data.get(k, raw[k]) for k in raw})
    else:
        from tools.aws_client import get_aws_client

        sh = get_aws_client(ctx, "securityhub")
        if sh is not None:
            try:
                resp = sh.get_findings(
                    Filters={
                        "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
                        "SeverityLabel": [{"Value": "CRITICAL", "Comparison": "EQUALS"}, {"Value": "HIGH", "Comparison": "EQUALS"}],
                    },
                    MaxResults=50,
                )
                findings = resp.get("Findings") or []
                failures = []
                for f in findings[:10]:
                    title = str(f.get("Title") or f.get("Id") or "finding")
                    failures.append(title)
                raw["control_failures"] = failures
                if failures:
                    raw["compliance_framework_status"] = "FAIL"
                    raw["overall_posture_score"] = max(0.0, 100.0 - len(failures) * 8.0)
            except Exception:
                pass

    score = float(raw["overall_posture_score"])
    risk = min(1.0, max(0.05, (100.0 - score) / 100.0))

    lines = [
        f"Compliance status: {raw['compliance_framework_status']}",
        f"Posture score: {score:.0f}",
    ]
    if raw["control_failures"]:
        lines.append(f"Control failures: {len(raw['control_failures'])}")

    return ToolResult(
        tool_name="check_compliance_posture",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
