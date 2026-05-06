"""Public request-access lead capture and superadmin lead management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_superadmin
from app.models.tenant import AccessLead, Tenant
from app.models.user import User
from app.routers.admin_tenants import TenantCreate

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadCreateBody(BaseModel):
    organization_name: str = Field(min_length=1, max_length=255)
    contact_name: str = Field(min_length=1, max_length=255)
    work_email: str = Field(min_length=3, max_length=255)
    website: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=2000)


class LeadOut(BaseModel):
    id: int
    organization_name: str
    contact_name: str
    work_email: str
    website: str
    notes: str
    status: str
    converted_tenant_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class LeadConvertBody(BaseModel):
    tenant_name: str = Field(min_length=1, max_length=255)
    tenant_slug: str = Field(min_length=1, max_length=64)


@router.post("/request-access", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_request_access_lead(body: LeadCreateBody, db: Session = Depends(get_db)):
    lead = AccessLead(
        organization_name=body.organization_name.strip(),
        contact_name=body.contact_name.strip(),
        work_email=body.work_email.strip().lower(),
        website=body.website.strip(),
        notes=body.notes.strip(),
        status="new",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return LeadOut(**lead.__dict__)


@router.get("", response_model=list[LeadOut])
def list_leads(db: Session = Depends(get_db), _super: User = Depends(require_superadmin)):
    rows = db.execute(select(AccessLead).order_by(AccessLead.created_at.desc())).scalars().all()
    return [LeadOut(**r.__dict__) for r in rows]


@router.post("/{lead_id}/convert", response_model=LeadOut)
def convert_lead_to_tenant(
    lead_id: int,
    body: LeadConvertBody,
    db: Session = Depends(get_db),
    _super: User = Depends(require_superadmin),
):
    lead = db.get(AccessLead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if lead.status == "converted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lead already converted")

    tenant_spec = TenantCreate(name=body.tenant_name.strip(), slug=body.tenant_slug)
    existing = db.execute(select(Tenant).where(Tenant.slug == tenant_spec.slug)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant slug already exists")
    tenant = Tenant(name=tenant_spec.name, slug=tenant_spec.slug, is_active=True)
    db.add(tenant)
    db.flush()

    lead.status = "converted"
    lead.converted_tenant_id = tenant.id
    lead.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(lead)
    return LeadOut(**lead.__dict__)
