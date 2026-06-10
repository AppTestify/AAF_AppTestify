"""FinOps agent — cost and budget signals."""

from __future__ import annotations

from typing import TYPE_CHECKING
from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme
from agents.base import run_agent_llm_flow

if TYPE_CHECKING:
    from app.services.llm_runtime import ActiveProvider

SYSTEM_PROMPT = (
    "You are a FinOps and cloud cost governance agent. "
    "Assess cloud infrastructure costs, budget variances, and cost anomaly events. "
    "Analyze the provided evidence records and output a structured assessment. "
    "Focus on cost spikes, unexpected resource scaling, and budget limits."
)


def run(
    evidence: list[EvidenceRecord],
    llm_providers: list[ActiveProvider] | None = None,
) -> AgentOpinion:
    evidence_slice = [e for e in evidence if e.source == "finops"]

    def fallback() -> AgentOpinion:
        refs: list[str] = []
        cost_stress = 0.0
        claim = "No material cost anomalies in evidence."
        theme = RiskTheme.LOW_RISK

        for e in evidence_slice:
            refs.append(f"{e.kind}:{e.summary[:48]}")
            cost_stress = max(cost_stress, e.severity)
            if e.severity > 0.45:
                claim = "Cloud spend or budget variance requires attention."
                theme = RiskTheme.COST_RISK
            elif "anomal" in e.kind.lower() or "spike" in e.kind.lower():
                claim = "Cost anomaly or spike detected."
                theme = RiskTheme.COST_RISK

        conf = 0.35 + 0.55 * min(1.0, cost_stress)
        return AgentOpinion(
            agent_id="finops",
            claim=claim,
            confidence=round(conf, 3),
            evidence_refs=refs[:12],
            risk_theme=theme,
            raw_signals={"cost_stress": cost_stress},
        )

    return run_agent_llm_flow(
        agent_id="finops",
        evidence_slice=evidence_slice,
        system_prompt=SYSTEM_PROMPT,
        fallback_fn=fallback,
        llm_providers=llm_providers,
    )
