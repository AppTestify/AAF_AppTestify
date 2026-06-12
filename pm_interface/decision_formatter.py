"""Format pipeline output for PMs and executives."""

from __future__ import annotations

import json
from typing import Any

from aaf.schema import (
    AgentOpinion,
    ConsensusResult,
    EvidenceRecord,
    ExplainabilityResult,
    PipelineResult,
    PMFormattedDecision,
    RARResult,
    UtilityResult,
)


def to_pm_decision(result: PipelineResult) -> PMFormattedDecision:
    title = _title(result.utility)
    summary = _summary_markdown(result)
    detail: dict[str, Any] = {
        "consensus_score": result.consensus.consensus_score,
        "rar_triggered": result.rar.rar_triggered,
        "rar_loops": result.rar.rar_loops,
        "recommended_action": result.utility.recommended_action.value,
        "utility_score": result.utility.utility_score,
        "xi_score": result.explainability.xi_score,
        "connectors": result.connectors_used,
        "guardrails": result.guardrails,
        "llm_cost": result.llm_cost,
    }
    return PMFormattedDecision(title=title, summary_markdown=summary, detail_json=detail)


def _title(u: UtilityResult) -> str:
    return f"Recommended: {u.recommended_action.value.replace('_', ' ').title()}"


def _summary_markdown(r: PipelineResult) -> str:
    parts = [
        f"**Executive summary:** Consensus **{r.consensus.consensus_score:.2f}**; "
        f"utility-selected action **`{r.utility.recommended_action.value}`** "
        f"(score {r.utility.utility_score:.2f}). "
        f"Explainability (XI) **{r.explainability.xi_score:.2f}**.",
    ]
    if r.rar.rar_triggered:
        parts.append(
            f"RAR ran **{r.rar.rar_loops}** loop(s); consensus moved from "
            f"{r.rar.consensus_before:.2f} to **{r.rar.consensus_after:.2f}**."
        )
    parts.append("")
    parts.append("### Top agent claims")
    for o in r.agent_opinions[:6]:
        parts.append(f"- **{o.agent_id}:** {o.claim}")
    return "\n".join(parts)


def pipeline_result_to_jsonable(result: PipelineResult) -> dict[str, Any]:
    """Serialize for API responses."""
    return json.loads(result.model_dump_json())
