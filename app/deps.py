from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from aaf.config import Settings, get_settings
from app.db import get_db
from app.models.rbac import Permission, Role, RolePermission, UserRoleBinding
from app.models.user import User
from app.security import decode_access_token

security_bearer = HTTPBearer(auto_error=False)


@lru_cache
def settings_dep() -> Settings:
    return get_settings()


def get_current_user(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security_bearer)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub = decode_access_token(creds.credentials, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(sub)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from exc
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_current_active_user(current: User = Depends(get_current_user)) -> User:
    if not current.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return current


def require_superadmin(current: User = Depends(get_current_active_user)) -> User:
    if not current.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin privileges required",
        )
    return current


def require_tenant_admin_or_superadmin(current: User = Depends(get_current_active_user)) -> User:
    """Batch / heavy tenant-wide operations: tenant admin or platform superadmin."""
    if current.is_superadmin or current.is_admin:
        return current
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Tenant admin or superadmin privileges required",
    )


def user_permissions(db: Session, user: User) -> set[str]:
    if user.is_superadmin:
        rows = (
            db.execute(
                select(Permission.code)
                .select_from(Role)
                .join(RolePermission, RolePermission.role_id == Role.id)
                .join(Permission, Permission.id == RolePermission.permission_id)
                .where(Role.tenant_id.is_(None), Role.name == "superadmin")
            )
            .scalars()
            .all()
        )
        return set(rows)
    if user.tenant_id is None:
        return set()
    rows = (
        db.execute(
            select(Permission.code)
            .select_from(UserRoleBinding)
            .join(Role, Role.id == UserRoleBinding.role_id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(UserRoleBinding.user_id == user.id)
        )
        .scalars()
        .all()
    )
    return set(rows)


def require_permission(permission_code: str):
    def _dep(
        db: Session = Depends(get_db),
        current: User = Depends(get_current_active_user),
    ) -> User:
        perms = user_permissions(db, current)
        if permission_code in perms:
            return current
        # Backward-compat fallback to current coarse role booleans.
        if permission_code in {"settings.manage", "cases.manage", "decisions.approve"} and (
            current.is_superadmin or current.is_admin
        ):
            return current
        if permission_code == "runs.create":
            return current
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission required: {permission_code}",
        )

    return _dep
