"""Login and current user."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from aaf.config import Settings
from app.deps import get_current_active_user, settings_dep
from app.db import get_db
from app.models.governance import AuditEvent
from app.models.tenant import Tenant
from app.models.user import User
from app.routers.admin_tenants import TenantCreate
from app.security import create_access_token, hash_password, verify_password
from app.validators.email import AuthEmail

router = APIRouter(prefix="/auth", tags=["auth"])
_FAILED: dict[str, tuple[int, datetime]] = {}
_MAX_LOGIN_ATTEMPTS = 8
_LOGIN_WINDOW = timedelta(minutes=10)


class LoginRequest(BaseModel):
    email: AuthEmail
    password: str = Field(min_length=1, max_length=128)


class UserPublic(BaseModel):
    id: int
    email: str
    is_superadmin: bool
    is_admin: bool
    tenant_id: Optional[int] = None
    tenant_slug: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


def user_to_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        is_superadmin=user.is_superadmin,
        is_admin=user.is_admin,
        tenant_id=user.tenant_id,
        tenant_slug=user.tenant.slug if user.tenant else None,
    )


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserPublic


class SignupStatusResponse(BaseModel):
    tenant_signup_enabled: bool


class TenantSignupRequest(BaseModel):
    organization_name: str = Field(min_length=1, max_length=255)
    tenant_slug: str = Field(min_length=1, max_length=64)
    admin_email: AuthEmail
    password: str = Field(min_length=8, max_length=128)


@router.get("/signup-status", response_model=SignupStatusResponse)
def signup_status(settings: Settings = Depends(settings_dep)):
    return SignupStatusResponse(tenant_signup_enabled=settings.public_tenant_signup_enabled)


@router.post("/signup-tenant", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def signup_tenant(
    body: TenantSignupRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    if not settings.public_tenant_signup_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant self-service signup is disabled",
        )
    try:
        tenant_spec = TenantCreate.model_validate(
            {"name": body.organization_name.strip(), "slug": body.tenant_slug}
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    email = str(body.admin_email).strip().lower()
    dup_slug = db.execute(select(Tenant).where(Tenant.slug == tenant_spec.slug)).scalar_one_or_none()
    if dup_slug:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization URL slug is already taken")
    dup_email = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if dup_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    tenant = Tenant(name=tenant_spec.name, slug=tenant_spec.slug, is_active=True)
    db.add(tenant)
    db.flush()
    user = User(
        email=email,
        hashed_password=hash_password(body.password),
        is_superadmin=False,
        is_admin=True,
        tenant_id=tenant.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    expire_minutes = settings.access_token_expire_minutes
    token = create_access_token(
        subject=str(user.id),
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expire_minutes=expire_minutes,
    )
    return LoginResponse(
        access_token=token,
        expires_in=expire_minutes * 60,
        user=user_to_public(user),
    )


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    email = body.email.strip().lower()
    now = datetime.now(timezone.utc)
    failed = _FAILED.get(email)
    if failed and failed[0] >= _MAX_LOGIN_ATTEMPTS and now - failed[1] < _LOGIN_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
        )
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        if failed and now - failed[1] < _LOGIN_WINDOW:
            _FAILED[email] = (failed[0] + 1, failed[1])
        else:
            _FAILED[email] = (1, now)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    _FAILED.pop(email, None)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    if user.tenant and not user.tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant is disabled")

    expire_minutes = settings.access_token_expire_minutes
    token = create_access_token(
        subject=str(user.id),
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expire_minutes=expire_minutes,
    )
    db.add(
        AuditEvent(
            tenant_id=user.tenant_id,
            actor_user_id=user.id,
            area="auth",
            action="login_success",
            entity_type="user",
            entity_id=user.id,
            summary=f"User {user.email} logged in",
        )
    )
    db.commit()
    return LoginResponse(
        access_token=token,
        expires_in=expire_minutes * 60,
        user=user_to_public(user),
    )


@router.get("/me", response_model=UserPublic)
def me(current: User = Depends(get_current_active_user)):
    return user_to_public(current)
