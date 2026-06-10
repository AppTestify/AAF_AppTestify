"""Project management agent — JIRA / delivery signals."""

from __future__ import annotations

from typing import TYPE_CHECKING
from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme
from agents.base import run_agent_llm_flow

if TYPE_CHECKING:
    from app.services.llm_runtime import ActiveProvider

SYSTEM_PROMPT = (
    "You are a Project Management and agile delivery governance agent. "
    "Assess project milestone progress, sprint metrics, issue blockers, and ticket delays. "
    "Analyze the provided evidence records and output a structured assessment. "
    "Focus on blocked delivery tasks, overdue items, and defect density."
)


def run(
    evidence: list[EvidenceRecord],
    llm_providers: list[ActiveProvider] | None = None,
) -> AgentOpinion:
    evidence_slice = [e for e in evidence if e.source == "jira"]

    def fallback() -> AgentOpinion:
        refs: list[str] = []
        stress = 0.0
        claim = "Delivery signals appear stable."
        theme = RiskTheme.LOW_RISK

        for e in evidence_slice:
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

    return run_agent_llm_flow(
        agent_id="project_management",
        evidence_slice=evidence_slice,
        system_prompt=SYSTEM_PROMPT,
        fallback_fn=fallback,
        llm_providers=llm_providers,
    )
