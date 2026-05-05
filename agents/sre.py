"""SRE / reliability agent."""

from __future__ import annotations

from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme


def run(evidence: list[EvidenceRecord]) -> AgentOpinion:
    refs: list[str] = []
    sev = 0.0
    claim = "No explicit SRE degradation signals in evidence."
    theme = RiskTheme.LOW_RISK

    for e in evidence:
        if e.metadata.get("sre_relevant") or "incident" in e.kind.lower() or "latenc" in e.kind.lower():
            refs.append(f"{e.source}:{e.summary[:40]}")
            sev = max(sev, e.severity)
            claim = "Service or reliability stress suggested by evidence."
            theme = RiskTheme.RELIABILITY_RISK
    # GitHub workflow failure can proxy SRE
    for e in evidence:
        if e.source == "github" and "workflow" in e.kind.lower() and e.severity > 0.5:
            sev = max(sev, e.severity * 0.8)
            if theme == RiskTheme.LOW_RISK:
                claim = "Build/check failures may impact production reliability."
                theme = RiskTheme.RELIABILITY_RISK

    conf = 0.4 + 0.45 * min(1.0, sev)
    return AgentOpinion(
        agent_id="sre",
        claim=claim,
        confidence=round(conf, 3),
        evidence_refs=refs[:12] or ["sre:indirect"],
        risk_theme=theme,
        raw_signals={"sre_severity": sev},
    )
