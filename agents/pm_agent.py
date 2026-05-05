"""Project management agent — JIRA / delivery signals."""

from __future__ import annotations

from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme


def run(evidence: list[EvidenceRecord]) -> AgentOpinion:
    refs: list[str] = []
    stress = 0.0
    claim = "Delivery signals appear stable."
    theme = RiskTheme.LOW_RISK

    for e in evidence:
        if e.source != "jira":
            continue
        refs.append(f"{e.kind}:{e.summary[:48]}")
        stress = max(stress, e.severity)
        kl = e.kind.lower()
        if "blocked" in kl or "overdue" in kl:
            claim = "Sprint or delivery items are blocked or overdue."
            theme = RiskTheme.DELIVERY_RISK
        elif "bug" in kl or "defect" in kl:
            claim = "Unresolved defects may affect release readiness."
            theme = RiskTheme.DELIVERY_RISK

    conf = 0.35 + 0.55 * min(1.0, stress)
    return AgentOpinion(
        agent_id="project_management",
        claim=claim,
        confidence=round(conf, 3),
        evidence_refs=refs[:12],
        risk_theme=theme,
        raw_signals={"delivery_stress": stress},
    )
