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
    results: dict[str, list[dict[str, Any]]] = {"decisions": [], "runs": [], "evidence": [], "cases": []}
    if not q:
        return {"query": query, "groups": results, "total": 0}

    from app.services.search_index import search_opensearch

    os_results = search_opensearch(tenant_id=tenant_id, query=query, limit=limit)
    if os_results is not None:
        total = sum(len(v) for v in os_results.values())
        return {"query": query, "groups": os_results, "total": total, "backend": "opensearch"}

    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    like = f"%{q}%"

    from concurrent.futures import ThreadPoolExecutor
    from app.db import SessionLocal

    def _fetch_runs():
        with SessionLocal() as session:
            rq = select(GovernanceRun).where(
                GovernanceRun.created_at >= since,
                or_(GovernanceRun.prompt.ilike(like), GovernanceRun.prompt_id.ilike(like)),
            )
            if tenant_id is not None:
                rq = rq.where(GovernanceRun.tenant_id == tenant_id)
            rows = session.execute(rq.limit(limit)).scalars().all()
            return [{"id": r.id, "prompt": r.prompt[:200], "status": r.status, "created_at": r.created_at.isoformat()} for r in rows]

    def _fetch_cases():
        with SessionLocal() as session:
            cq = select(GovernanceCase).where(
                GovernanceCase.created_at >= since,
                GovernanceCase.title.ilike(like),
            )
            if tenant_id is not None:
                cq = cq.where(GovernanceCase.tenant_id == tenant_id)
            rows = session.execute(cq.limit(limit)).scalars().all()
            return [{"id": c.id, "title": c.title, "status": c.status} for c in rows]

    def _fetch_evidence():
        with SessionLocal() as session:
            sq = select(EvidenceSnapshot).join(GovernanceRun, GovernanceRun.id == EvidenceSnapshot.run_id).where(
                GovernanceRun.created_at >= since,
                EvidenceSnapshot.connector_name.ilike(like),
            )
            if tenant_id is not None:
                sq = sq.where(GovernanceRun.tenant_id == tenant_id)
            rows = session.execute(sq.limit(limit)).scalars().all()
            return [{"id": s.id, "run_id": s.run_id, "connector": s.connector_name} for s in rows]

    with ThreadPoolExecutor(max_workers=3) as executor:
        f_runs = executor.submit(_fetch_runs)
        f_cases = executor.submit(_fetch_cases)
        f_evidence = executor.submit(_fetch_evidence)

        results["runs"] = f_runs.result()
        results["cases"] = f_cases.result()
        results["evidence"] = f_evidence.result()

    total = sum(len(v) for v in results.values())
    return {"query": query, "groups": results, "total": total}
