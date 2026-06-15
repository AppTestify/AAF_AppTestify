"""Fetch connector evidence, normalize, and run the pipeline."""

from __future__ import annotations

from typing import Any

from aaf.config import Settings
from aaf.schema import EvidenceRecord, PipelineResult
from app.services.llm_runtime import ActiveProvider
from guardrails.llm_cost_tracker import LlmCostTracker
from guardrails.pipeline import run_input_guards, run_pm_prompt_guard
from llm.intent_router import route_pm_intent
from orchestrator.connector_router import route_connectors_semantic
from orchestrator.evidence import collect_evidence
from orchestrator.pipeline import run_pipeline


async def run_governance(
    prompt: str,
    prompt_id: str | None,
    settings: Settings,
    llm_providers: list[ActiveProvider] | None = None,
    *,
    tenant_ui_preferences: dict[str, Any] | None = None,
) -> PipelineResult:
    input_reports: list = []
    cost_tracker = LlmCostTracker()

    pm_outcome = run_pm_prompt_guard(prompt, settings)
    prompt = pm_outcome.prompt
    input_reports.extend(pm_outcome.reports)

    router_result = route_pm_intent(
        prompt,
        settings=settings,
        llm_providers=llm_providers,
        cost_tracker=cost_tracker,
    )
    intent_payload = router_result.to_intent_payload(pipeline_phase=settings.pipeline_phase)

    names, _routing_confidence = route_connectors_semantic(prompt)
    for connector in router_result.connectors:
        if connector not in names:
            names.append(connector)
    ctx: dict[str, str] = {
        "prompt": prompt,
        "github_repo": settings.github_repo,
        "jira_project": settings.jira_project,
    }
    raw, normalized, evidence_package, tool_ctx = await collect_evidence(
        settings=settings,
        prompt=prompt,
        connector_names=names,
        ctx=ctx,
        tenant_ui_preferences=tenant_ui_preferences,
        warm_tools=settings.pipeline_phase >= 3,
    )
    guard_outcome = run_input_guards(
        prompt,
        normalized,
        raw,
        settings,
        pm_already_checked=True,
    )
    prompt = guard_outcome.prompt
    normalized = guard_outcome.evidence
    input_reports.extend(guard_outcome.reports)
    evidence_package["records"] = [r.model_dump(mode="json") for r in normalized]
    if tool_ctx.evidence_package is not None:
        tool_ctx.evidence_package["records"] = evidence_package["records"]

    async def live_refresh_evidence() -> list[EvidenceRecord]:
        raw_fresh, normalized_fresh, package_fresh, refreshed_ctx = await collect_evidence(
            settings=settings,
            prompt=prompt,
            connector_names=names,
            ctx=ctx,
            tenant_ui_preferences=tenant_ui_preferences,
            warm_tools=True,
        )
        del package_fresh, refreshed_ctx
        fresh_outcome = run_input_guards(
            prompt,
            normalized_fresh,
            raw_fresh,
            settings,
            pm_already_checked=True,
        )
        return fresh_outcome.evidence

    return await run_pipeline(
        prompt=prompt,
        prompt_id=prompt_id,
        settings=settings,
        normalized_evidence=normalized,
        raw_evidence_by_connector=raw,
        connectors_used=names,
        llm_providers=llm_providers or [],
        live_refresh_evidence=live_refresh_evidence,
        tool_ctx=tool_ctx,
        input_guard_reports=input_reports,
        agent_ids=router_result.agents_needed,
        intent=intent_payload,
        cost_tracker=cost_tracker,
        evidence_package=evidence_package,
    )
