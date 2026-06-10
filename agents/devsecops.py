"""DevSecOps agent — policy / security posture."""

from __future__ import annotations

from typing import TYPE_CHECKING
from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme
from agents.base import run_agent_llm_flow

if TYPE_CHECKING:
    from app.services.llm_runtime import ActiveProvider

SYSTEM_PROMPT = (
    "You are a DevSecOps and cloud security governance agent. "
    "Assess security compliance violations, vulnerability scans, secret exposures, and access control anomalies. "
    "Analyze the provided evidence records and output a structured assessment. "
    "Focus on software vulnerabilities, policy violations, and security warnings."
)


def run(
    evidence: list[EvidenceRecord],
    llm_providers: list[ActiveProvider] | None = None,
) -> AgentOpinion:
    evidence_slice = []
    for e in evidence:
        kl = (e.kind + " " + e.summary).lower()
        if any(x in kl for x in ("security", "policy", "vuln", "secret", "devsec")):
            evidence_slice.append(e)

    def fallback() -> AgentOpinion:
        refs: list[str] = []
        risk = 0.0
        claim = "No security policy violations flagged in evidence."
        theme = RiskTheme.LOW_RISK

        for e in evidence_slice:
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

    return run_agent_llm_flow(
        agent_id="devsecops",
        evidence_slice=evidence_slice,
        system_prompt=SYSTEM_PROMPT,
        fallback_fn=fallback,
        llm_providers=llm_providers,
    )
