"""Login and current user."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from aaf.config import Settings
from app.deps import get_current_active_user, settings_dep
from app.db import get_db
from app.models.governance import AuditEvent
from app.models.tenant import Tenant
from app.models.user import User, AuthRateLimit
from app.routers.admin_tenants import TenantCreate
from app.security import create_access_token, hash_password, verify_password
from app.validators.email import AuthEmail

router = APIRouter(prefix="/auth", tags=["auth"])


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
    response: Response,
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
    
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=expire_minutes * 60,
    )
    
    return LoginResponse(user=user_to_public(user))


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    email = body.email.strip().lower()
    now = datetime.now(timezone.utc)
    
    rate_limit = db.execute(select(AuthRateLimit).where(AuthRateLimit.email == email)).scalar_one_or_none()
    window = timedelta(minutes=settings.rate_limit_window_minutes)
    
    if rate_limit:
        last_attempt = rate_limit.last_attempt_at
        if last_attempt.tzinfo is None:
            last_attempt = last_attempt.replace(tzinfo=timezone.utc)
            
        if rate_limit.failed_attempts >= settings.rate_limit_max_attempts and now - last_attempt < window:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Please try again later.",
            )

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        if not rate_limit:
            rate_limit = AuthRateLimit(email=email, failed_attempts=1, last_attempt_at=now)
            db.add(rate_limit)
        else:
            last_attempt = rate_limit.last_attempt_at
            if last_attempt.tzinfo is None:
                last_attempt = last_attempt.replace(tzinfo=timezone.utc)
                
            if now - last_attempt < window:
                rate_limit.failed_attempts += 1
            else:
                rate_limit.failed_attempts = 1
            rate_limit.last_attempt_at = now
            
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
        
    if rate_limit:
        db.delete(rate_limit)
        db.commit()
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
    
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=expire_minutes * 60,
    )
    
    return LoginResponse(user=user_to_public(user))


@router.get("/me", response_model=UserPublic)
def me(current: User = Depends(get_current_active_user)):
    return user_to_public(current)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token", httponly=True, secure=True, samesite="strict")
    return {"message": "Logged out successfully"}
