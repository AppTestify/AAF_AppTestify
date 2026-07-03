"""Template-based explanation without external LLM."""

from __future__ import annotations

from aaf.schema import (
    AgentOpinion,
    ConsensusResult,
    GovernanceAction,
    RARResult,
    UtilityResult,
    GovernanceDecision,
)
from app.services.llm_runtime import ActiveProvider
from typing import Any

def generate_explanation(
    decision: GovernanceDecision,
    llm_providers: list[ActiveProvider] | None = None,
    tracker: Any = None,
) -> tuple[str, dict[str, Any]]:
    """Phase 1 single constrained LLM call to explain the decision."""
    deterministic = build_explanation(
        prompt=decision.prompt,
        opinions=decision.opinions,
        consensus=decision.consensus,
        rar=decision.rar,
        utility=decision.utility,
    )
    
    if not llm_providers:
        return deterministic, {"status": "degraded", "reason": "no_active_provider"}
        
    if not tracker:
        from guardrails.llm_cost_tracker import LlmCostTracker
        tracker = LlmCostTracker()
    
    # We restrict context to just the structured JSON for tokens/cost.
    # We avoid passing raw signals or tool logic.
    decision_json = decision.model_dump_json(exclude={"opinions": {"__all__": {"raw_signals"}}})
    
    prompt = (
        "Create a concise executive governance explanation in markdown with sections: "
        "What we evaluated, Consensus, Recommended action, Why trustworthy. "
        "The response must be brief (~500 tokens max) and rely ONLY on the provided JSON.\n"
        "Critically: Incorporate the specific agent 'evidence' strings into your explanation narrative "
        "(e.g., if the evidence mentions 'payments-service', use that exact detail).\n\n"
        f"JSON Context:\n{decision_json}"
    )
    
    try:
        llm_text, meta = tracker.invoke_tracked(
            llm_providers,
            prompt,
            phase="explanation",
            agent_id="orchestrator",
        )
        if llm_text.strip():
            return llm_text.strip()[:1000], {"status": "ok", **meta}
    except Exception:
        return deterministic, {
            "status": "degraded",
            "reason": "invocation_failed",
            "providers_attempted": [p.provider_name for p in llm_providers],
        }
    
    return deterministic, {"status": "degraded", "reason": "empty_output"}


def build_explanation(
    *,
    prompt: str,
    opinions: list[AgentOpinion],
    consensus: ConsensusResult,
    rar: RARResult,
    utility: UtilityResult,
) -> str:
    lines: list[str] = []
    lines.append("## What we evaluated")
    lines.append(f"- **Your question:** {prompt}")
    lines.append("")
    lines.append("## Domain perspectives")
    for o in opinions:
        lines.append(
            f"- **{o.agent_id}** ({o.risk_theme.value}, confidence {o.confidence:.2f}): {o.claim}"
        )
        for ev in o.evidence:
            lines.append(f"  - {ev}")
    lines.append("")
    lines.append("## Consensus")
    lines.append(
        f"- Score **{consensus.consensus_score:.2f}** — {consensus.notes or 'theme alignment across agents.'}"
    )
    if consensus.dominant_theme:
        lines.append(f"- Dominant theme: `{consensus.dominant_theme.value}`.")
    lines.append("")
    lines.append("## RAR (Re-Grounded Agentic Reasoning)")
    if rar.rar_triggered:
        lines.append(
            f"- Triggered because initial consensus ({rar.consensus_before:.2f}) was below threshold."
        )
        lines.append(f"- Loops executed: **{rar.rar_loops}**. Consensus after: **{rar.consensus_after:.2f}**.")
        for n in rar.reground_notes[:5]:
            lines.append(f"  - {n}")
    else:
        lines.append("- Not triggered; agreement was sufficient without re-grounding.")
    lines.append("")
    lines.append("## Recommended action")
    action_label = _action_label(utility.recommended_action)
    lines.append(
        f"- **{action_label}** (utility score **{utility.utility_score:.3f}** using weights "
        f"w_perf={utility.weights_used.get('w_perf', 0):.2f}, "
        f"w_cost={utility.weights_used.get('w_cost', 0):.2f}, "
        f"w_risk={utility.weights_used.get('w_risk', 0):.2f})."
    )
    lines.append("- Runner-up scores (for audit):")
    for k, v in sorted(utility.scores_by_action.items(), key=lambda x: -x[1])[:5]:
        lines.append(f"  - `{k}`: {v:.3f}")
    lines.append("")
    lines.append("## Why this is trustworthy")
    lines.append(
        "- The recommendation combines **consensus** across domains with **utility** weighting for "
        "performance, cost, and risk — not a single noisy signal."
    )
    return "\n".join(lines)


def _action_label(a: GovernanceAction) -> str:
    return {
        GovernanceAction.ROLLBACK: "Rollback to stable deployment",
        GovernanceAction.MITIGATE_MONITOR: "Mitigate and monitor",
        GovernanceAction.SCALE_ADJUST: "Scale / capacity adjustment",
        GovernanceAction.PATCH_BLOCK_RELEASE: "Patch or block release",
        GovernanceAction.HOLD_RELEASE: "Hold release",
        GovernanceAction.OBSERVE: "No immediate action / observe",
    }.get(a, a.value)
