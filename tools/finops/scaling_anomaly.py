"""Scaling anomaly detector — instance_delta, orphan_scale_flag, thrash_events."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.aws_client import get_aws_client
from tools.context import ToolContext
from tools.finops._aws_data import load_finops_bundle


async def detect_scaling_anomaly(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    bundle = await load_finops_bundle(ctx)

    raw: dict[str, Any] = {
        "instance_delta": bundle.get("instance_delta", 0),
        "orphan_scale_flag": bool(bundle.get("orphan_scale_flag")),
        "thrash_events": bundle.get("thrash_events", 0),
        "spot_interruptions": bundle.get("spot_interruptions", 0),
    }

    if not ctx.sim_mode:
        asg = get_aws_client(ctx, "autoscaling")
        cw = get_aws_client(ctx, "cloudwatch")
        if asg is not None:
            try:
                start = now - timedelta(hours=24)
                activities = asg.describe_scaling_activities(MaxRecords=50)
                recent = [
                    a
                    for a in activities.get("Activities") or []
                    if a.get("StartTime") and a["StartTime"].replace(tzinfo=timezone.utc) >= start
                ]
                raw["thrash_events"] = len(recent)
                raw["instance_delta"] = len(recent)
            except Exception:
                pass
        if cw is not None:
            try:
                # Heuristic: scale-out without traffic proxy
                raw["orphan_scale_flag"] = raw["thrash_events"] > 2
            except Exception:
                pass

    risk = min(
        1.0,
        int(raw["instance_delta"]) * 0.08
        + int(raw["thrash_events"]) * 0.1
        + (0.4 if raw["orphan_scale_flag"] else 0),
    )

    lines = [
        f"Instance count delta: {raw['instance_delta']}",
        f"Scaling thrash events (24h): {raw['thrash_events']}",
    ]
    if raw["orphan_scale_flag"]:
        lines.append("Scale-out without traffic increase detected")

    return ToolResult(
        tool_name="detect_scaling_anomaly",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
