"""Governance API routes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from aaf.config import Settings
from app.deps import get_current_active_user, require_tenant_admin_or_superadmin, settings_dep
from app.db import get_db
from app.models.config import TenantSettings
from app.models.governance import EvidenceSnapshot, GovernanceRun
from app.models.metrics import LLMCallLog
from app.models.user import User
from app.services.config_resolver import (
    apply_pipeline_overrides,
    get_ai_runtime_summary,
    resolve_effective_settings,
    resolve_tenant_for_user,
)
from app.services.run_payload import enrich_run_payload
from guardrails.budget_cap import enforce_budget_cap
from guardrails.exceptions import GuardrailBlockedError
from guardrails.pm_prompt_guard import check_pm_prompt
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
    if effective.guardrails_enabled and tenant:
        try:
            enforce_budget_cap(db, tenant.id, ts_row, effective)
        except GuardrailBlockedError as exc:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "budget_exceeded",
                    "guard": exc.result.guard_name,
                    "violations": [v.model_dump() for v in exc.result.violations],
                },
            ) from exc
    if effective.guardrails_enabled:
        guard = check_pm_prompt(body.prompt, effective)
        if guard.blocked:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "guardrail_blocked",
                    "guard": guard.guard_name,
                    "violations": [v.model_dump() for v in guard.violations],
                },
            )
    provider_chain = resolve_provider_chain(db, tenant)
    try:
        result = await run_governance(
            body.prompt,
            body.prompt_id,
            effective,
            llm_providers=provider_chain,
            tenant_ui_preferences=(ts_row.ui_preferences if ts_row else None),
        )
    except GuardrailBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "guardrail_blocked",
                "guard": exc.result.guard_name,
                "violations": [v.model_dump() for v in exc.result.violations],
            },
        ) from exc
    out = pipeline_result_to_jsonable(result)

    # Persist run + evidence snapshots so Evidence Hub has data
    run = GovernanceRun(
        tenant_id=tenant.id if tenant else None,
        requested_by_user_id=user.id,
        prompt=body.prompt,
        prompt_id=body.prompt_id,
        status="succeeded",
        result_json=out,
        runtime_config_json={"tenant_slug": tenant.slug if tenant else None},
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()
    evidence_by_connector = out.get("raw_evidence_by_connector") or {}
    if isinstance(evidence_by_connector, dict):
        for connector_name, payload in evidence_by_connector.items():
            db.add(
                EvidenceSnapshot(
                    run_id=run.id,
                    connector_name=str(connector_name),
                    payload_json=payload if isinstance(payload, dict) else {"payload": payload},
                )
            )
    llm_cost = out.get("llm_cost") if isinstance(out.get("llm_cost"), dict) else {}
    for call in (llm_cost.get("calls") or []):
        if not isinstance(call, dict):
            continue
        db.add(
            LLMCallLog(
                run_id=run.id,
                tenant_id=run.tenant_id,
                agent_id=str(call.get("agent_id") or "unknown"),
                provider_name=str(call.get("provider_name") or "unknown"),
                model_name=str(call.get("model_name") or "unknown"),
                prompt_tokens=int(call.get("prompt_tokens") or 0),
                completion_tokens=int(call.get("completion_tokens") or 0),
                cost_usd=float(call.get("cost_usd") or 0.0),
                latency_ms=int(call.get("latency_ms") or 0),
            )
        )
    db.commit()
    out["run_id"] = run.id

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
    return enrich_run_payload(out, db=db, tenant=tenant, settings=effective, ts_row=ts_row)


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
        r = await run_governance(
            text,
            pid,
            effective,
            llm_providers=provider_chain,
            tenant_ui_preferences=(ts_row.ui_preferences if ts_row else None),
        )
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
