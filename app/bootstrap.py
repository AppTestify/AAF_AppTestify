"""Create tables and bootstrap tenants + superadmin + tenant admin."""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from aaf.config import Settings
from app.db import Base, get_engine
from app.models.policy import GovernancePolicy
from app.models.rbac import Permission, Role, RolePermission, UserRoleBinding
from app.models.tenant import Tenant
from app.models.user import User
from app.routers.admin_tenants import TenantCreate
from app.security import hash_password

_log = logging.getLogger(__name__)


def create_tables() -> None:
    from app.models import config as _config  # noqa: F401
    from app.models import governance as _governance  # noqa: F401
    from app.models import policy as _policy  # noqa: F401
    from app.models import rbac as _rbac  # noqa: F401
    from app.models import tenant as _tenant  # noqa: F401
    from app.models import user as _user  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def ensure_default_tenant(db: Session, settings: Settings) -> Tenant:
    slug = settings.default_tenant_slug.strip().lower()
    t = db.execute(select(Tenant).where(Tenant.slug == slug)).scalar_one_or_none()
    if t:
        return t
    tenant = Tenant(
        name=settings.default_tenant_name.strip() or "Default organization",
        slug=slug,
        is_active=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def ensure_superadmin_user(db: Session, settings: Settings) -> Optional[User]:
    email = settings.superadmin_email.strip().lower()
    if not email:
        return None
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        return None
    user = User(
        email=email,
        hashed_password=hash_password(settings.superadmin_password),
        is_superadmin=True,
        is_admin=False,
        tenant_id=None,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_tenant_admin_user(db: Session, settings: Settings, tenant: Tenant) -> Optional[User]:
    """Tenant-scoped admin on the default tenant (not platform superadmin)."""
    email = settings.admin_email.strip().lower()
    super_email = settings.superadmin_email.strip().lower()
    if not email or email == super_email:
        return None
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        return None
    user = User(
        email=email,
        hashed_password=hash_password(settings.admin_password),
        is_superadmin=False,
        is_admin=True,
        tenant_id=tenant.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_test_tenant_admin(db: Session, settings: Settings) -> None:
    """Create an extra tenant (e.g. slug `test`) and a tenant admin user when enabled."""
    if not settings.seed_test_tenant:
        return
    try:
        tc = TenantCreate.model_validate(
            {"name": settings.test_tenant_name.strip(), "slug": settings.test_tenant_slug}
        )
    except ValidationError:
        _log.warning("Invalid test tenant name/slug; skipping test tenant seed")
        return

    default_slug = settings.default_tenant_slug.strip().lower()
    if tc.slug == default_slug:
        _log.warning("test_tenant_slug matches default_tenant_slug; skipping test tenant seed")
        return

    test_email = settings.test_tenant_admin_email.strip().lower()
    super_e = settings.superadmin_email.strip().lower()
    admin_e = settings.admin_email.strip().lower()
    if not test_email or test_email in (super_e, admin_e):
        _log.warning(
            "test_tenant_admin_email must be set and differ from superadmin and default admin; "
            "skipping test tenant seed"
        )
        return

    tenant = db.execute(select(Tenant).where(Tenant.slug == tc.slug)).scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(name=tc.name, slug=tc.slug, is_active=True)
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

    existing_user = db.execute(select(User).where(User.email == test_email)).scalar_one_or_none()
    if existing_user is None:
        user = User(
            email=test_email,
            hashed_password=hash_password(settings.test_tenant_admin_password),
            is_superadmin=False,
            is_admin=True,
            tenant_id=tenant.id,
            is_active=True,
        )
        db.add(user)
        db.commit()


def backfill_user_tenant_ids(db: Session, tenant: Tenant) -> int:
    """Assign default tenant to users missing tenant_id (excluding superadmins)."""
    users = (
        db.execute(select(User).where(User.tenant_id.is_(None), User.is_superadmin == False))
        .scalars()
        .all()
    )
    n = 0
    for u in users:
        u.tenant_id = tenant.id
        n += 1
    if n:
        db.commit()
    return n


def bootstrap_tenancy(db: Session, settings: Settings) -> None:
    """Default tenant, superadmin, tenant admin, then backfill legacy users."""
    tenant = ensure_default_tenant(db, settings)
    super_user = ensure_superadmin_user(db, settings)
    tenant_admin = ensure_tenant_admin_user(db, settings, tenant)
    ensure_test_tenant_admin(db, settings)
    backfill_user_tenant_ids(db, tenant)
    ensure_rbac_defaults(db, tenant, super_user, tenant_admin)
    ensure_default_policy(db, tenant)


def ensure_default_policy(db: Session, tenant: Tenant) -> None:
    existing = db.execute(
        select(GovernancePolicy).where(GovernancePolicy.tenant_id == tenant.id, GovernancePolicy.name == "default")
    ).scalar_one_or_none()
    if existing is not None:
        return
    db.add(
        GovernancePolicy(
            tenant_id=tenant.id,
            name="default",
            consensus_min=0.55,
            xi_min=0.5,
            require_rar_clear=True,
        )
    )
    db.commit()


def ensure_rbac_defaults(db: Session, tenant: Tenant, super_user: Optional[User], tenant_admin: Optional[User]) -> None:
    permission_codes = {
        "runs.create": "Create governance runs",
        "cases.manage": "Create and update governance cases",
        "decisions.approve": "Approve governance decisions",
        "settings.manage": "Update tenant settings",
    }
    perm_ids: dict[str, int] = {}
    for code, desc in permission_codes.items():
        p = db.execute(select(Permission).where(Permission.code == code)).scalar_one_or_none()
        if p is None:
            p = Permission(code=code, description=desc)
            db.add(p)
            db.flush()
        perm_ids[code] = p.id

    def ensure_role(name: str, tenant_id: Optional[int], description: str, codes: list[str]) -> Role:
        role = db.execute(select(Role).where(Role.name == name, Role.tenant_id == tenant_id)).scalar_one_or_none()
        if role is None:
            role = Role(name=name, tenant_id=tenant_id, description=description)
            db.add(role)
            db.flush()
        for code in codes:
            rp = db.execute(
                select(RolePermission).where(RolePermission.role_id == role.id, RolePermission.permission_id == perm_ids[code])
            ).scalar_one_or_none()
            if rp is None:
                db.add(RolePermission(role_id=role.id, permission_id=perm_ids[code]))
        return role

    super_role = ensure_role(
        "superadmin",
        None,
        "Platform super administrator",
        ["runs.create", "cases.manage", "decisions.approve", "settings.manage"],
    )
    admin_role = ensure_role(
        "tenant_admin",
        tenant.id,
        "Tenant administrator",
        ["runs.create", "cases.manage", "decisions.approve", "settings.manage"],
    )
    reviewer_role = ensure_role("reviewer", tenant.id, "Tenant reviewer", ["runs.create"])

    def bind(user: Optional[User], role: Role) -> None:
        if user is None:
            return
        exists = db.execute(
            select(UserRoleBinding).where(UserRoleBinding.user_id == user.id, UserRoleBinding.role_id == role.id)
        ).scalar_one_or_none()
        if exists is None:
            db.add(UserRoleBinding(user_id=user.id, role_id=role.id))

    bind(super_user, super_role)
    bind(tenant_admin, admin_role)

    # Give all non-admin default-tenant users reviewer role.
    users = db.execute(select(User).where(User.tenant_id == tenant.id, User.is_admin == False)).scalars().all()  # noqa: E712
    for u in users:
        bind(u, reviewer_role)
    db.commit()
