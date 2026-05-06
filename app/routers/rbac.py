"""RBAC helper APIs."""

from __future__ import annotations

import secrets
import string
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_active_user, require_tenant_admin_or_superadmin, user_permissions
from app.models.config import TenantNotificationConfig
from app.models.rbac import Role, UserRoleBinding
from app.models.tenant import Tenant
from app.models.user import User
from app.security import hash_password
from app.services.email_runtime import send_templated_email

router = APIRouter(prefix="/rbac", tags=["rbac"])


class MePermissionsOut(BaseModel):
    permissions: list[str]


class UserAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_admin: bool
    is_superadmin: bool
    is_active: bool
    tenant_id: Optional[int] = None
    role_names: list[str] = []


class UserCreateIn(BaseModel):
    email: str
    role_name: str = "reviewer"
    is_active: bool = True


@router.get("/me/permissions", response_model=MePermissionsOut)
def get_my_permissions(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    perms = sorted(user_permissions(db, current))
    return MePermissionsOut(permissions=perms)


def _resolve_tenant_for_scope(db: Session, actor: User, tenant_slug: Optional[str]) -> Tenant:
    if actor.is_superadmin:
        if tenant_slug:
            tenant = db.execute(select(Tenant).where(Tenant.slug == tenant_slug.strip().lower())).scalar_one_or_none()
            if tenant is None:
                raise HTTPException(status_code=404, detail="Target tenant not found")
            return tenant
        tenant = db.execute(select(Tenant).order_by(Tenant.slug)).scalars().first()
        if tenant is None:
            raise HTTPException(status_code=404, detail="No tenants available")
        return tenant
    if actor.tenant_id is None:
        raise HTTPException(status_code=403, detail="User has no tenant scope")
    tenant = db.get(Tenant, actor.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


def _generate_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.get("/users", response_model=list[UserAdminOut])
def list_users(
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(require_tenant_admin_or_superadmin),
):
    tenant = _resolve_tenant_for_scope(db, current, tenant_slug)
    users = db.execute(select(User).where(User.tenant_id == tenant.id).order_by(User.created_at.desc())).scalars().all()
    role_map: dict[int, list[str]] = {}
    if users:
        bindings = db.execute(
            select(UserRoleBinding.user_id, Role.name)
            .join(Role, Role.id == UserRoleBinding.role_id)
            .where(UserRoleBinding.user_id.in_([u.id for u in users]))
        ).all()
        for user_id, role_name in bindings:
            role_map.setdefault(int(user_id), []).append(str(role_name))
    return [
        UserAdminOut(
            id=u.id,
            email=u.email,
            is_admin=u.is_admin,
            is_superadmin=u.is_superadmin,
            is_active=u.is_active,
            tenant_id=u.tenant_id,
            role_names=sorted(role_map.get(u.id, [])),
        )
        for u in users
    ]


@router.post("/users")
def create_user(
    body: UserCreateIn,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(require_tenant_admin_or_superadmin),
):
    tenant = _resolve_tenant_for_scope(db, current, tenant_slug)
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="valid email is required")
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="User email already exists")

    role_name = body.role_name.strip().lower()
    if role_name not in {"reviewer", "tenant_admin"}:
        raise HTTPException(status_code=422, detail="role_name must be reviewer or tenant_admin")
    role = db.execute(select(Role).where(Role.tenant_id == tenant.id, Role.name == role_name)).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found for tenant")

    temporary_password = _generate_password()
    user = User(
        email=email,
        hashed_password=hash_password(temporary_password),
        is_superadmin=False,
        is_admin=role_name == "tenant_admin",
        tenant_id=tenant.id,
        is_active=body.is_active,
    )
    db.add(user)
    db.flush()
    db.add(UserRoleBinding(user_id=user.id, role_id=role.id))
    db.commit()

    delivery_status = "not_configured"
    try:
        notif = db.execute(select(TenantNotificationConfig).where(TenantNotificationConfig.tenant_id == tenant.id)).scalar_one_or_none()
        if notif and notif.notifications_enabled:
            send_templated_email(
                notif,
                template_key="user_welcome",
                to_email=email,
                values={"user_email": email, "tenant_slug": tenant.slug, "temporary_password": temporary_password},
            )
            delivery_status = "sent"
    except Exception as exc:  # noqa: BLE001
        delivery_status = f"failed: {exc}"

    return {
        "id": user.id,
        "email": user.email,
        "role_name": role_name,
        "tenant_id": user.tenant_id,
        "delivery_status": delivery_status,
        "temporary_password": None if delivery_status == "sent" else temporary_password,
    }
