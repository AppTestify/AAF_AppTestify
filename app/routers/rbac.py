"""RBAC helper APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_active_user, user_permissions
from app.models.user import User

router = APIRouter(prefix="/rbac", tags=["rbac"])


class MePermissionsOut(BaseModel):
    permissions: list[str]


@router.get("/me/permissions", response_model=MePermissionsOut)
def get_my_permissions(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    perms = sorted(user_permissions(db, current))
    return MePermissionsOut(permissions=perms)
