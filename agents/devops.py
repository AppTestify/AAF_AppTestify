"""DevOps agent — engineering / release signals."""

from __future__ import annotations

from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme


def run(evidence: list[EvidenceRecord]) -> AgentOpinion:
    refs: list[str] = []
    worst = 0.0
    claim = "No DevOps risk signals."
    theme = RiskTheme.LOW_RISK

    for e in evidence:
        if e.source != "github":
            continue
        refs.append(f"{e.kind}:{e.summary[:48]}")
        worst = max(worst, e.severity)
        kl = e.kind.lower()
        if "workflow_fail" in kl or "failed" in kl:
            claim = "CI/CD or workflow failures detected."
            theme = RiskTheme.OPERATIONAL_RISK
        elif "pr" in kl and "block" in kl:
            claim = "PR or merge activity suggests release friction."
            theme = RiskTheme.DELIVERY_RISK
        elif "commit" in kl and e.severity > 0.5:
            claim = "Recent changes may correlate with operational risk."
            theme = RiskTheme.OPERATIONAL_RISK

    conf = 0.35 + 0.5 * min(1.0, worst)
    if theme == RiskTheme.LOW_RISK:
        conf = 0.4
    return AgentOpinion(
        agent_id="devops",
        claim=claim,
        confidence=round(conf, 3),
        evidence_refs=refs[:12],
        risk_theme=theme,
        raw_signals={"github_severity": worst},
    )
