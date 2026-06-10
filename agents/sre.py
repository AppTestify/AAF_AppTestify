"""SRE / reliability agent."""

from __future__ import annotations

from typing import TYPE_CHECKING
from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme
from agents.base import run_agent_llm_flow

if TYPE_CHECKING:
    from app.services.llm_runtime import ActiveProvider

SYSTEM_PROMPT = (
    "You are a Site Reliability Engineering (SRE) governance agent. "
    "Assess site reliability, incident reports, system performance metrics, and service degradation signals. "
    "Analyze the provided evidence records and output a structured assessment. "
    "Focus on service availability, latency, errors, and system warnings."
)


def run(
    evidence: list[EvidenceRecord],
    llm_providers: list[ActiveProvider] | None = None,
) -> AgentOpinion:
    evidence_slice = [
        e for e in evidence
        if e.metadata.get("sre_relevant")
        or "incident" in e.kind.lower()
        or "latenc" in e.kind.lower()
        or (e.source == "github" and "workflow" in e.kind.lower() and e.severity > 0.5)
    ]

    def fallback() -> AgentOpinion:
        refs: list[str] = []
        sev = 0.0
        claim = "No explicit SRE degradation signals in evidence."
        theme = RiskTheme.LOW_RISK

        for e in evidence_slice:
            if e.metadata.get("sre_relevant") or "incident" in e.kind.lower() or "latenc" in e.kind.lower():
                refs.append(f"{e.source}:{e.summary[:40]}")
                sev = max(sev, e.severity)
                claim = "Service or reliability stress suggested by evidence."
                theme = RiskTheme.RELIABILITY_RISK
        # GitHub workflow failure can proxy SRE
        for e in evidence_slice:
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

    return run_agent_llm_flow(
        agent_id="sre",
        evidence_slice=evidence_slice,
        system_prompt=SYSTEM_PROMPT,
        fallback_fn=fallback,
        llm_providers=llm_providers,
    )
