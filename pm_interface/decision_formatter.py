"""Format pipeline output for PMs and executives."""

from __future__ import annotations

import json
from typing import Any

from aaf.schema import (
    AgentOpinion,
    ConsensusResult,
    EvidenceRecord,
    ExplainabilityResult,
    GovernanceBrief,
    PipelineResult,
    PMFormattedDecision,
    RARResult,
    UtilityResult,
)
from agents.display import resolve_display_label


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
        label = resolve_display_label(o.agent_id, o.display_id)
        parts.append(f"- **{label}:** {o.claim}")
        for ev in o.evidence:
            parts.append(f"  - {ev}")
    return "\n".join(parts)


def build_governance_brief_from_result(result: PipelineResult) -> GovernanceBrief:
    source = "llm" if result.llm_invocation.get("status") == "ok" else "deterministic"
    return GovernanceBrief(
        markdown=result.explanation,
        executive_title=result.pm_view.title or _title(result.utility),
        executive_summary=result.pm_view.summary_markdown.split("\n")[0] if result.pm_view.summary_markdown else "",
        audit_detail={
            "guardrails": result.guardrails,
            "llm_cost": result.llm_cost,
            "intent": result.intent,
            "agents_activated": result.agents_activated,
            "xi_score": result.explainability.xi_score,
        },
        source=source,
    )


def build_governance_brief(out: dict[str, Any]) -> dict[str, Any]:
    """Build governance_brief dict from serialized run payload."""
    pm = out.get("pm_view") if isinstance(out.get("pm_view"), dict) else {}
    utility = out.get("utility") if isinstance(out.get("utility"), dict) else {}
    explain = out.get("explainability") if isinstance(out.get("explainability"), dict) else {}
    llm_inv = out.get("llm_invocation") if isinstance(out.get("llm_invocation"), dict) else {}
    source = "llm" if llm_inv.get("status") == "ok" else "deterministic"
    title = pm.get("title") or ""
    if not title and utility.get("recommended_action"):
        title = f"Recommended: {str(utility['recommended_action']).replace('_', ' ').title()}"
    summary_md = pm.get("summary_markdown") or ""
    agents_activated = out.get("agents_activated")
    if not agents_activated:
        agents_activated = [
            o.get("agent_id")
            for o in (out.get("agent_opinions") or [])
            if isinstance(o, dict) and o.get("agent_id")
        ]
    return {
        "markdown": out.get("explanation") or "",
        "executive_title": title,
        "executive_summary": summary_md.split("\n")[0] if summary_md else "",
        "audit_detail": {
            "guardrails": out.get("guardrails") or {},
            "llm_cost": out.get("llm_cost") or {},
            "intent": out.get("intent") or {},
            "agents_activated": agents_activated,
            "xi_score": explain.get("xi_score"),
        },
        "source": source,
    }


def pipeline_result_to_jsonable(result: PipelineResult) -> dict[str, Any]:
    """Serialize for API responses."""
    payload = json.loads(result.model_dump_json())
    payload["agent_outputs"] = payload.get("agent_opinions") or []
    if result.governance_brief is None:
        payload["governance_brief"] = build_governance_brief(payload)
    return payload
