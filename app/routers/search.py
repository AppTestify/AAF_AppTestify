"""Global search API."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_current_active_user
from app.db import get_db
from app.models.user import User
from app.services.config_resolver import resolve_tenant_for_user
from app.services.search import global_search

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(
    q: str = Query(min_length=1),
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    tenant = resolve_tenant_for_user(db, user, tenant_slug)
    return global_search(db, tenant_id=tenant.id if tenant else None, query=q)
