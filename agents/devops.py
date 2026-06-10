"""DevOps agent — engineering / release signals."""

from __future__ import annotations

from typing import TYPE_CHECKING
from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme
from agents.base import run_agent_llm_flow

if TYPE_CHECKING:
    from app.services.llm_runtime import ActiveProvider

SYSTEM_PROMPT = (
    "You are a DevOps and release engineering governance agent. "
    "Assess risks associated with CI/CD pipelines, code repository events, and PR activities. "
    "Analyze the provided evidence records and output a structured assessment. "
    "Focus on delivery velocity, workflow failures, and change impact."
)


def run(
    evidence: list[EvidenceRecord],
    llm_providers: list[ActiveProvider] | None = None,
) -> AgentOpinion:
    evidence_slice = [e for e in evidence if e.source == "github"]

    def fallback() -> AgentOpinion:
        refs: list[str] = []
        worst = 0.0
        claim = "No DevOps risk signals."
        theme = RiskTheme.LOW_RISK

        for e in evidence_slice:
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

    return run_agent_llm_flow(
        agent_id="devops",
        evidence_slice=evidence_slice,
        system_prompt=SYSTEM_PROMPT,
        fallback_fn=fallback,
        llm_providers=llm_providers,
    )
