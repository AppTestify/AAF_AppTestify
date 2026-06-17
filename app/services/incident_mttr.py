"""Correlate PagerDuty incidents to DORA MTTR metrics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.metrics import DeploymentEvent


def correlate_incident_to_mttr(
    db: Session,
    tenant_id: int,
    incident_id: str,
    service_name: str,
    incident_start: datetime,
    incident_end: Optional[datetime] = None,
    mttr_hours: Optional[float] = None,
) -> bool:
    """
    Correlate a PagerDuty incident to a recent deployment and update MTTR.
    
    Strategy:
    1. Find deployments for the service within the incident window
    2. Match incident_start to a deployment (deployment_at within incident window)
    3. If incident_end exists, calculate/use mttr_hours
    4. Update DeploymentEvent metadata with incident_id and mttr_hours
    5. Mark deployment as rollback=True if incident was severe
    
    Returns: True if correlation was successful, False if no matching deployment found.
    """
    if not incident_end and not mttr_hours:
        # Cannot correlate without end time or explicit MTTR
        return False
    
    # Calculate MTTR if not provided
    if not mttr_hours and incident_end:
        mttr = (incident_end - incident_start).total_seconds() / 3600.0
        mttr_hours = mttr
    
    # Search for recent deployments (within 24 hours before incident start)
    search_start = incident_start - timedelta(hours=24)
    
    stmt = select(DeploymentEvent).where(
        and_(
            DeploymentEvent.tenant_id == tenant_id,
            DeploymentEvent.service_name == service_name,
            DeploymentEvent.deployed_at >= search_start,
            DeploymentEvent.deployed_at <= incident_start,
        )
    ).order_by(DeploymentEvent.deployed_at.desc())
    
    rows = db.execute(stmt).scalars().all()
    
    if not rows:
        return False
    
    # Correlate to the most recent deployment before incident
    deployment = rows[0]
    
    # Update metadata with incident correlation
    metadata = deployment.metadata_json or {}
    metadata.setdefault("incidents", []).append({
        "id": incident_id,
        "started_at": incident_start.isoformat(),
        "ended_at": incident_end.isoformat() if incident_end else None,
        "mttr_hours": mttr_hours,
    })
    metadata["mttr_hours"] = mttr_hours
    
    # Mark as rollback if incident was significant (no explicit rollback flag, but MTTR > 1 hour)
    if mttr_hours and mttr_hours > 1.0 and not deployment.succeeded:
        deployment.rollback = True
    
    deployment.metadata_json = metadata
    db.add(deployment)
    db.commit()
    
    return True


def batch_correlate_incidents(
    db: Session,
    tenant_id: int,
    incidents: list[dict],
) -> dict[str, bool]:
    """
    Batch correlate multiple incidents to deployments.
    
    Expected incident dict format:
    {
        "id": "INC001",
        "service_name": "payment-service",
        "started_at": datetime,
        "resolved_at": datetime (optional),
        "mttr_hours": float (optional),
    }
    
    Returns: dict mapping incident_id -> success (True/False)
    """
    results = {}
    for incident in incidents:
        success = correlate_incident_to_mttr(
            db=db,
            tenant_id=tenant_id,
            incident_id=incident.get("id", ""),
            service_name=incident.get("service_name", ""),
            incident_start=incident.get("started_at"),
            incident_end=incident.get("resolved_at"),
            mttr_hours=incident.get("mttr_hours"),
        )
        results[incident.get("id", "")] = success
    
    return results
