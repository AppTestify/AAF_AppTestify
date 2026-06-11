"""End-to-end governance pipeline."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aaf.config import Settings
from aaf.schema import EvidenceRecord, PMFormattedDecision, PipelineResult
from agents.registry import run_all_agents_async
from tools.context import ToolContext, build_tool_context
from connectors.evidence_normalizer import enrich_for_rar
from llm.deterministic_explainer import build_explanation
from app.services.llm_runtime import ActiveProvider, invoke_text_with_failover
from metrics.explainability import compute_xi
from orchestrator.rar import run_rar_loop_async
from orchestrator.utility import score_actions
from pm_interface.decision_formatter import to_pm_decision


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
) -> PipelineResult:
    """Run agents → consensus → RAR → utility → explainability → PM view."""

    ctx = tool_ctx or build_tool_context(settings)

    async def rerun_agents(ev: list[EvidenceRecord], _loop: int) -> list[Any]:
        return await run_all_agents_async(
            ev,
            tool_ctx=ctx,
            settings=settings,
            llm_providers=llm_providers,
        )

    lr = live_refresh_evidence if settings.rar_live_refresh_enabled else None

    def llm_reground(opinions: list[Any], evidence: list[EvidenceRecord]) -> str:
        if not llm_providers:
            return ""
        prompt = (
            "Agents disagree on risk themes. Summarize the conflict and what additional evidence "
            "would resolve it in one sentence. Context: "
            + str({"opinions": [o.model_dump() for o in opinions], "evidence_count": len(evidence)})
        )
        try:
            text, _ = invoke_text_with_failover(llm_providers, prompt)
            return text.strip()[:500]
        except Exception:
            return ""

    initial_opinions = await run_all_agents_async(
        normalized_evidence,
        tool_ctx=ctx,
        settings=settings,
        llm_providers=llm_providers,
    )
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
    if llm_providers:
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
            llm_text, meta = invoke_text_with_failover(llm_providers, llm_prompt)
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
    xi = compute_xi(
        evidence=normalized_evidence,
        opinions=opinions,
        consensus=consensus_result,
        utility=utility_result,
        explanation_text=explanation,
    )

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
    )
    return result.model_copy(update={"pm_view": to_pm_decision(result)})
