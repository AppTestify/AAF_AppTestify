"""End-to-end governance pipeline."""

from __future__ import annotations

from typing import Any

from aaf.config import Settings
from aaf.schema import EvidenceRecord, PMFormattedDecision, PipelineResult
from agents.registry import run_all_agents
from connectors.evidence_normalizer import enrich_for_rar
from llm.deterministic_explainer import build_explanation
from metrics.explainability import compute_xi
from orchestrator.rar import run_rar_loop
from orchestrator.utility import score_actions
from pm_interface.decision_formatter import to_pm_decision


def run_pipeline(
    *,
    prompt: str,
    prompt_id: str | None,
    settings: Settings,
    normalized_evidence: list[EvidenceRecord],
    raw_evidence_by_connector: dict[str, Any],
    connectors_used: list[str],
) -> PipelineResult:
    """Run agents → consensus → RAR → utility → explainability → PM view."""

    def rerun_agents(ev: list[EvidenceRecord], _loop: int) -> list[Any]:
        return run_all_agents(ev)

    opinions, rar_result, consensus_result = run_rar_loop(
        initial_evidence=normalized_evidence,
        initial_opinions=run_all_agents(normalized_evidence),
        tau=settings.tau_consensus,
        max_loops=settings.max_rar_loops,
        settings=settings,
        rerun_agents=rerun_agents,
        enrich_evidence=enrich_for_rar,
    )

    utility_result = score_actions(normalized_evidence, settings)
    explanation = build_explanation(
        prompt=prompt,
        opinions=opinions,
        consensus=consensus_result,
        rar=rar_result,
        utility=utility_result,
    )
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
    )
    return result.model_copy(update={"pm_view": to_pm_decision(result)})
