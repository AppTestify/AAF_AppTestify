"""End-to-end governance pipeline."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aaf.config import Settings
from aaf.schema import EvidenceRecord, PMFormattedDecision, PipelineResult
from agents import devops, devsecops, finops, pm_agent
from agents.registry import run_agents_async
from tools.context import ToolContext, build_tool_context
from connectors.evidence_normalizer import enrich_for_rar
from llm.deterministic_explainer import build_explanation
from app.services.llm_runtime import ActiveProvider
from metrics.explainability import compute_xi
from guardrails.llm_cost_tracker import LlmCostTracker
from guardrails.brief_output_guard import guard_brief_output
from guardrails.pipeline import (
    apply_agent_output_guards,
    guardrail_report_dict,
    run_tool_scope_guards_for_agents,
)
from guardrails.types import GuardrailResult
from orchestrator.rar import run_rar_loop_async
from orchestrator.utility import score_actions
from pm_interface.decision_formatter import to_pm_decision


def _agent_tool_plans() -> dict[str, list[str]]:
    return {
        devops.DevOpsAgent.agent_id: [fn.__name__ for fn in devops.DevOpsAgent().tool_callables()],
        finops.FinOpsAgent.agent_id: [fn.__name__ for fn in finops.FinOpsAgent().tool_callables()],
        devsecops.DevSecOpsAgent.agent_id: [fn.__name__ for fn in devsecops.DevSecOpsAgent().tool_callables()],
        pm_agent.PMAgent.agent_id: [fn.__name__ for fn in pm_agent.PMAgent().tool_callables()],
    }


def _refresh_tools_from_opinions(opinions: list[Any]) -> list[str] | None:
    names: list[str] = []
    for opinion in opinions:
        called = opinion.raw_signals.get("tools_called")
        if isinstance(called, list):
            names.extend(str(name) for name in called if name)
    deduped = list(dict.fromkeys(names))
    return deduped or None


async def run_pipeline(
    *,
    prompt: str,
    prompt_id: str | None,
    settings: Settings,
    normalized_evidence: list[EvidenceRecord],
    raw_evidence_by_connector: dict[str, Any],
    connectors_used: list[str],
    llm_providers: list[ActiveProvider] | None = None,
    live_refresh_evidence: Callable[[], Awaitable[list[EvidenceRecord]]] | None = None,
    tool_ctx: ToolContext | None = None,
    input_guard_reports: list[GuardrailResult] | None = None,
    agent_ids: list[str] | None = None,
    intent: dict[str, Any] | None = None,
    cost_tracker: LlmCostTracker | None = None,
    evidence_package: dict[str, Any] | None = None,
) -> PipelineResult:
    """Run agents → consensus → RAR → utility → explainability → PM view."""

    ctx = tool_ctx or build_tool_context(settings)
    if evidence_package and ctx.evidence_package is None:
        ctx.evidence_package = evidence_package
    all_guard_reports: list[GuardrailResult] = list(input_guard_reports or [])
    tracker = cost_tracker or LlmCostTracker()

    activated = agent_ids or ["devops", "finops", "devsecops", "project_management"]
    plans = _agent_tool_plans()
    filtered_plans = {aid: plans[aid] for aid in activated if aid in plans}
    all_guard_reports.extend(run_tool_scope_guards_for_agents(filtered_plans, settings))

    async def _run_agents(
        ev: list[EvidenceRecord],
        *,
        refresh_tools: list[str] | None = None,
    ) -> list[Any]:
        return await run_agents_async(
            ev,
            activated,
            tool_ctx=ctx,
            settings=settings,
            llm_providers=llm_providers,
            refresh_tools=refresh_tools,
            cost_tracker=tracker,
        )

    latest_opinions: list[Any] = []

    async def rerun_agents(ev: list[EvidenceRecord], _loop: int) -> list[Any]:
        refresh = _refresh_tools_from_opinions(latest_opinions or initial_opinions)
        ops = await _run_agents(ev, refresh_tools=refresh)
        guarded, reports = apply_agent_output_guards(ops, settings)
        all_guard_reports.extend(reports)
        latest_opinions.clear()
        latest_opinions.extend(guarded)
        return guarded

    lr = live_refresh_evidence if settings.rar_live_refresh_enabled else None

    def llm_reground(opinions: list[Any], evidence: list[EvidenceRecord]) -> str:
        if not llm_providers or len(tracker.calls) >= settings.max_llm_calls_per_run:
            return ""
        reground_prompt = (
            "Agents disagree on risk themes. Summarize the conflict and what additional evidence "
            "would resolve it in one sentence. Context: "
            + str({"opinions": [o.model_dump() for o in opinions], "evidence_count": len(evidence)})
        )
        try:
            text, _ = tracker.invoke_tracked(
                llm_providers,
                reground_prompt,
                phase="rar_reground",
                agent_id="orchestrator",
            )
            return text.strip()[:500]
        except Exception:
            return ""

    initial_opinions_raw = await _run_agents(normalized_evidence)
    initial_opinions, initial_guard_reports = apply_agent_output_guards(initial_opinions_raw, settings)
    all_guard_reports.extend(initial_guard_reports)
    latest_opinions.extend(initial_opinions)

    opinions, rar_result, consensus_result = await run_rar_loop_async(
        initial_evidence=normalized_evidence,
        initial_opinions=initial_opinions,
        tau=settings.tau_consensus,
        max_loops=settings.max_rar_loops,
        rerun_agents=rerun_agents,
        enrich_evidence=enrich_for_rar,
        live_refresh_evidence=lr,
        llm_reground=llm_reground if llm_providers else None,
    )

    utility_result = score_actions(normalized_evidence, settings, opinions=opinions)
    deterministic_explanation = build_explanation(
        prompt=prompt,
        opinions=opinions,
        consensus=consensus_result,
        rar=rar_result,
        utility=utility_result,
    )
    explanation = deterministic_explanation
    llm_meta: dict[str, Any] = {"status": "degraded", "reason": "no_active_provider"}
    if llm_providers and len(tracker.calls) < settings.max_llm_calls_per_run:
        llm_prompt = (
            "Create a concise executive governance explanation in markdown with sections: "
            "What we evaluated, Consensus, Recommended action, Why trustworthy. "
            "Use this JSON context:\n"
            + str(
                {
                    "prompt": prompt,
                    "consensus": consensus_result.model_dump(),
                    "rar": rar_result.model_dump(),
                    "utility": utility_result.model_dump(),
                    "opinions": [o.model_dump() for o in opinions],
                }
            )
        )
        try:
            llm_text, meta = tracker.invoke_tracked(
                llm_providers,
                llm_prompt,
                phase="explanation",
                agent_id="orchestrator",
            )
            if llm_text.strip():
                explanation = llm_text.strip()
                llm_meta = {"status": "ok", **meta}
        except Exception:  # noqa: BLE001
            explanation = deterministic_explanation
            llm_meta = {
                "status": "degraded",
                "reason": "invocation_failed",
                "providers_attempted": [p.provider_name for p in llm_providers],
            }

    explanation, brief_guard_report = guard_brief_output(
        explanation,
        deterministic_explanation=deterministic_explanation,
        utility=utility_result,
        consensus=consensus_result,
        opinions=opinions,
        evidence=normalized_evidence,
        settings=settings,
    )
    all_guard_reports.append(brief_guard_report)

    xi = compute_xi(
        evidence=normalized_evidence,
        opinions=opinions,
        consensus=consensus_result,
        utility=utility_result,
        explanation_text=explanation,
    )
    llm_cost = tracker.snapshot()
    llm_cost["max_llm_calls_per_run"] = settings.max_llm_calls_per_run
    llm_cost["budget_exhausted"] = len(tracker.calls) >= settings.max_llm_calls_per_run

    placeholder_pm = PMFormattedDecision(title="", summary_markdown="", detail_json={})
    result = PipelineResult(
        prompt=prompt,
        prompt_id=prompt_id,
        connectors_used=connectors_used,
        raw_evidence_by_connector=raw_evidence_by_connector,
        normalized_evidence=normalized_evidence,
        agent_opinions=opinions,
        consensus=consensus_result,
        rar=rar_result,
        utility=utility_result,
        explanation=explanation,
        explainability=xi,
        pm_view=placeholder_pm,
        llm_invocation=llm_meta,
        guardrails=guardrail_report_dict(all_guard_reports, settings=settings),
        llm_cost=llm_cost,
        intent=intent or {},
        agents_activated=activated,
        pipeline_phase=settings.pipeline_phase,
    )
    updated = result.model_copy(update={"pm_view": to_pm_decision(result)})
    from pm_interface.decision_formatter import build_governance_brief_from_result

    brief = build_governance_brief_from_result(updated)
    return updated.model_copy(update={"governance_brief": brief})
