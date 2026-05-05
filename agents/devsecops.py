"""DevSecOps agent — policy / security posture."""

from __future__ import annotations

from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme


def run(evidence: list[EvidenceRecord]) -> AgentOpinion:
    refs: list[str] = []
    risk = 0.0
    claim = "No security policy violations flagged in evidence."
    theme = RiskTheme.LOW_RISK

    for e in evidence:
        kl = (e.kind + " " + e.summary).lower()
        if any(x in kl for x in ("security", "policy", "vuln", "secret", "devsec")):
            refs.append(f"{e.source}:{e.summary[:40]}")
            risk = max(risk, e.severity)
            claim = "Security or policy risk indicated."
            theme = RiskTheme.SECURITY_RISK

    conf = 0.35 + 0.5 * min(1.0, risk)
    return AgentOpinion(
        agent_id="devsecops",
        claim=claim,
        confidence=round(conf, 3),
        evidence_refs=refs[:12] or ["devsec:baseline"],
        risk_theme=theme,
        raw_signals={"security_stress": risk},
    )
