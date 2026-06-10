"""RI coverage reader — ri_coverage_pct, ondemand_waste_usd, sp_utilisation_pct."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.aws_client import get_aws_client
from tools.context import ToolContext
from tools.finops._aws_data import load_finops_bundle


async def get_ri_coverage(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    bundle = await load_finops_bundle(ctx)

    raw: dict[str, Any] = {
        "ri_coverage_pct": bundle.get("ri_coverage_pct", 0.0),
        "ondemand_waste_usd": bundle.get("ondemand_waste_usd", 0.0),
        "sp_utilisation_pct": bundle.get("sp_utilisation_pct", 0.0),
        "ri_expiring_soon": bundle.get("ri_expiring_soon", 0),
    }

    if not ctx.sim_mode:
        ce = get_aws_client(ctx, "ce")
        ec2 = get_aws_client(ctx, "ec2")
        if ce is not None:
            try:
                cov = ce.get_reservation_coverage()
                for row in cov.get("CoveragesByTime") or []:
                    total = row.get("Total") or {}
                    raw["ri_coverage_pct"] = round(float(total.get("CoverageHours", {}).get("CoverageHoursPercentage") or 0), 2)
                sp = ce.get_savings_plans_coverage()
                for row in sp.get("SavingsPlansCoverages") or []:
                    raw["sp_utilisation_pct"] = round(float(row.get("Coverage", {}).get("CoveragePercentage") or 0), 2)
            except Exception:
                pass
        if ec2 is not None:
            try:
                ris = ec2.describe_reserved_instances()
                expiring = sum(1 for ri in ris.get("ReservedInstances") or [] if ri.get("State") == "active")
                raw["ri_expiring_soon"] = expiring
            except Exception:
                pass

    coverage = float(raw["ri_coverage_pct"])
    risk = min(1.0, max(0.0, (100 - coverage) / 100.0 * 0.5 + float(raw["ondemand_waste_usd"]) / 5000.0))

    lines = [
        f"RI coverage: {coverage:.1f}%",
        f"On-demand overspend: ${float(raw['ondemand_waste_usd']):.0f}",
        f"Savings Plans utilisation: {float(raw['sp_utilisation_pct']):.1f}%",
    ]
    if int(raw["ri_expiring_soon"]) > 0:
        lines.append(f"RIs expiring within 30 days: {raw['ri_expiring_soon']}")

    return ToolResult(
        tool_name="get_ri_coverage",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
