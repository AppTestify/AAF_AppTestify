"""DORA and platform metrics API."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_current_active_user
from app.db import get_db
from app.models.user import User
from app.services.config_resolver import resolve_tenant_for_user
from app.services.dora import compute_dora_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/dora")
def dora_metrics(
    tenant_slug: Optional[str] = Query(default=None),
    window_days: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    tenant = resolve_tenant_for_user(db, user, tenant_slug)
    if tenant is None:
        return {"error": "tenant_required"}
    return compute_dora_metrics(db, tenant.id, window_days=window_days)
