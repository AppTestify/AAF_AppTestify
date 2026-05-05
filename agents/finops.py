"""FinOps agent — cost and budget signals."""

from __future__ import annotations

from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme


def run(evidence: list[EvidenceRecord]) -> AgentOpinion:
    refs: list[str] = []
    cost_stress = 0.0
    claim = "No material cost anomalies in evidence."
    theme = RiskTheme.LOW_RISK

    for e in evidence:
        if e.source != "finops":
            continue
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
