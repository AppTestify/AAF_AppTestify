"""DORA metrics computation per tenant."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.metrics import DeploymentEvent


def compute_dora_metrics(db: Session, tenant_id: int, *, window_days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    rows = (
        db.execute(
            select(DeploymentEvent).where(
                DeploymentEvent.tenant_id == tenant_id,
                DeploymentEvent.deployed_at >= since,
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return {
            "window_days": window_days,
            "deployment_frequency_per_week": 0.0,
            "lead_time_hours_p50": None,
            "change_failure_rate": 0.0,
            "mttr_hours": None,
            "sample_size": 0,
        }

    total = len(rows)
    failures = sum(1 for r in rows if not r.succeeded or r.rollback)
    lead_times = sorted([r.lead_time_hours for r in rows if r.lead_time_hours is not None])
    p50 = lead_times[len(lead_times) // 2] if lead_times else None
    weeks = max(1.0, window_days / 7.0)
    freq = total / weeks

    mttr_values = [
        float((r.metadata_json or {}).get("mttr_hours", 0))
        for r in rows
        if r.rollback and (r.metadata_json or {}).get("mttr_hours")
    ]
    mttr = sum(mttr_values) / len(mttr_values) if mttr_values else None

    return {
        "window_days": window_days,
        "deployment_frequency_per_week": round(freq, 2),
        "lead_time_hours_p50": round(p50, 2) if p50 is not None else None,
        "change_failure_rate": round(failures / total, 4),
        "mttr_hours": round(mttr, 2) if mttr is not None else None,
        "sample_size": total,
    }
