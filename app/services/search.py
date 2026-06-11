"""Global search across governance entities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.governance import EvidenceSnapshot, GovernanceCase, GovernanceRun


def global_search(
    db: Session,
    *,
    tenant_id: Optional[int],
    query: str,
    window_days: int = 30,
    limit: int = 50,
) -> dict[str, Any]:
    q = query.strip().lower()
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    like = f"%{q}%"
    results: dict[str, list[dict[str, Any]]] = {"decisions": [], "runs": [], "evidence": [], "cases": []}
    if not q:
        return {"query": query, "groups": results, "total": 0}

    run_q = select(GovernanceRun).where(
        GovernanceRun.created_at >= since,
        or_(GovernanceRun.prompt.ilike(like), GovernanceRun.prompt_id.ilike(like)),
    )
    if tenant_id is not None:
        run_q = run_q.where(GovernanceRun.tenant_id == tenant_id)
    runs = db.execute(run_q.limit(limit)).scalars().all()
    results["runs"] = [
        {"id": r.id, "prompt": r.prompt[:200], "status": r.status, "created_at": r.created_at.isoformat()}
        for r in runs
    ]

    case_q = select(GovernanceCase).where(
        GovernanceCase.created_at >= since,
        GovernanceCase.title.ilike(like),
    )
    if tenant_id is not None:
        case_q = case_q.where(GovernanceCase.tenant_id == tenant_id)
    cases = db.execute(case_q.limit(limit)).scalars().all()
    results["cases"] = [{"id": c.id, "title": c.title, "status": c.status} for c in cases]

    if runs:
        run_ids = [r.id for r in runs]
        snaps = (
            db.execute(
                select(EvidenceSnapshot).where(
                    EvidenceSnapshot.run_id.in_(run_ids),
                    EvidenceSnapshot.connector_name.ilike(like),
                ).limit(limit)
            )
            .scalars()
            .all()
        )
        results["evidence"] = [
            {"id": s.id, "run_id": s.run_id, "connector": s.connector_name} for s in snaps
        ]

    total = sum(len(v) for v in results.values())
    return {"query": query, "groups": results, "total": total}
