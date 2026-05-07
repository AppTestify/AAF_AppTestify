"""Governance API routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from aaf.config import Settings
from app.deps import get_current_active_user, require_tenant_admin_or_superadmin, settings_dep
from app.db import get_db
from app.models.config import TenantSettings
from app.models.user import User
from app.services.config_resolver import (
    apply_pipeline_overrides,
    get_ai_runtime_summary,
    resolve_effective_settings,
    resolve_tenant_for_user,
)
from app.services.decision_framing import build_decision_framing
from app.services.governance_service import run_governance
from app.services.llm_runtime import resolve_provider_chain
from pm_interface.decision_formatter import pipeline_result_to_jsonable

router = APIRouter(prefix="/governance", tags=["governance"])

_ROOT = Path(__file__).resolve().parents[2]
_LIBRARY_PATH = _ROOT / "data" / "prompt_library.json"


class RunBody(BaseModel):
    prompt: str = Field(min_length=1)
    prompt_id: Optional[str] = None


@router.post("/run")
async def governance_run(
    body: RunBody,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
    user: User = Depends(get_current_active_user),
):
    tenant = resolve_tenant_for_user(db, user, tenant_slug)
    effective = resolve_effective_settings(db, settings, tenant)
    ts_row = (
        db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)).scalar_one_or_none()
        if tenant
        else None
    )
    effective = apply_pipeline_overrides(effective, ts_row)
    provider_chain = resolve_provider_chain(db, tenant)
    result = await run_governance(body.prompt, body.prompt_id, effective, llm_providers=provider_chain)
    out = pipeline_result_to_jsonable(result)
    out["decision_framing"] = build_decision_framing(out)
    out["runtime_config"] = {
        "tenant_slug": tenant.slug if tenant else None,
        "connector_mode": effective.connector_mode.value,
        "github_repo": effective.github_repo,
        "ai": get_ai_runtime_summary(db, tenant),
    }
    out["llm_invocation"] = out.get("llm_invocation") or {
        "status": "degraded",
        "reason": "no_active_provider",
    }
    return out


@router.post("/batch")
async def governance_batch(
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
    admin: User = Depends(require_tenant_admin_or_superadmin),
):
    tenant = resolve_tenant_for_user(db, admin, tenant_slug)
    effective = resolve_effective_settings(db, settings, tenant)
    ts_row = (
        db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)).scalar_one_or_none()
        if tenant
        else None
    )
    effective = apply_pipeline_overrides(effective, ts_row)
    provider_chain = resolve_provider_chain(db, tenant)
    data = json.loads(_LIBRARY_PATH.read_text(encoding="utf-8"))
    prompts = data.get("prompts") or []
    results: list[dict] = []
    for p in prompts:
        text = p.get("text") or ""
        pid = p.get("id")
        r = await run_governance(text, pid, effective, llm_providers=provider_chain)
        results.append(
            {
                "prompt_id": pid,
                "consensus": r.consensus.consensus_score,
                "rar_triggered": r.rar.rar_triggered,
                "recommended_action": r.utility.recommended_action.value,
                "xi": r.explainability.xi_score,
            }
        )
    return {
        "runs": results,
        "count": len(results),
        "runtime_config": {
            "tenant_slug": tenant.slug if tenant else None,
            "connector_mode": effective.connector_mode.value,
            "github_repo": effective.github_repo,
            "ai": get_ai_runtime_summary(db, tenant),
        },
        "llm_invocation": {"status": "ok" if provider_chain else "degraded", "providers": [p.provider_name for p in provider_chain]},
    }
