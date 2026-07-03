"""Shared enrichment for sync and async governance run API payloads."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from aaf.config import Settings
from app.models.config import TenantSettings
from app.models.tenant import Tenant
from app.services.decision_framing import build_decision_framing
from guardrails.budget_cap import budget_status_dict
from pm_interface.decision_formatter import build_governance_brief


def enrich_run_payload(
    out: dict[str, Any],
    *,
    db: Session,
    tenant: Optional[Tenant],
    settings: Settings,
    ts_row: Optional[TenantSettings] = None,
) -> dict[str, Any]:
    """Add decision_framing, governance_brief, llm_budget, and agent_outputs aliases."""
    enriched = dict(out)
    enriched["decision_framing"] = build_decision_framing(enriched)
    enriched["governance_brief"] = build_governance_brief(enriched)
    enriched["agent_outputs"] = enriched.get("agent_opinions") or []

    intent = enriched.get("intent")
    if isinstance(intent, dict):
        enriched["agents_activated"] = intent.get("agents_needed") or enriched.get("agents_activated")

    if tenant:
        enriched["llm_budget"] = budget_status_dict(db, tenant.id, ts_row)

    return enriched
