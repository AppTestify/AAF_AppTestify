"""Load FinOps AWS data from fixtures or live APIs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from tools.aws_client import get_aws_client
from tools.context import ToolContext
from tools.sim_data import load_finops_fixture, load_tools_fixture


async def load_finops_bundle(ctx: ToolContext) -> dict[str, Any]:
    if ctx.sim_mode:
        data = load_tools_fixture(ctx.fixtures_dir, "finops_aws")
        if data:
            return data
        legacy = load_finops_fixture(ctx.fixtures_dir)
        return {
            "daily_spend": legacy.get("daily_spend") or [],
            "anomaly_flag": bool(legacy.get("anomalies")),
            "wow_delta_pct": 15.0,
            "top_services": ["Amazon EC2"],
            "budget_pct_used": 60.0,
            "days_elapsed_pct": 33.0,
            "pace_ratio": 1.8,
            "forecast_overage": False,
            "alert_triggered": False,
            "instance_delta": 2,
            "orphan_scale_flag": bool(legacy.get("anomalies")),
            "thrash_events": 1,
            "spot_interruptions": 0,
            "cost_per_req": 0.003,
            "unit_delta_pct": 10.0,
            "top_unit_offenders": ["api"],
            "trend_direction": "up",
            "ri_coverage_pct": 70.0,
            "ondemand_waste_usd": 500.0,
            "sp_utilisation_pct": 80.0,
            "ri_expiring_soon": 0,
        }

    ce = get_aws_client(ctx, "ce")
    if ce is None:
        return {}

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=7)
    try:
        resp = ce.get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
    except Exception:
        return {}

    daily_spend: list[dict[str, Any]] = []
    service_totals: dict[str, float] = {}
    for row in resp.get("ResultsByTime") or []:
        day = row.get("TimePeriod", {}).get("Start")
        amount = 0.0
        for group in row.get("Groups") or []:
            svc = (group.get("Keys") or ["Unknown"])[0]
            val = float((group.get("Metrics") or {}).get("UnblendedCost", {}).get("Amount") or 0)
            amount += val
            service_totals[svc] = service_totals.get(svc, 0.0) + val
        daily_spend.append({"day": day, "amount_usd": round(amount, 2)})

    top_services = sorted(service_totals, key=service_totals.get, reverse=True)[:3]
    wow_delta_pct = 0.0
    if len(daily_spend) >= 2:
        first_half = sum(d["amount_usd"] for d in daily_spend[: len(daily_spend) // 2])
        second_half = sum(d["amount_usd"] for d in daily_spend[len(daily_spend) // 2 :])
        if first_half > 0:
            wow_delta_pct = round(((second_half - first_half) / first_half) * 100.0, 2)

    return {
        "daily_spend": daily_spend,
        "wow_delta_pct": wow_delta_pct,
        "top_services": top_services,
        "anomaly_flag": wow_delta_pct > 30.0,
    }
