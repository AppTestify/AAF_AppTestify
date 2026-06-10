"""Run all domain agents on normalized evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING
from aaf.schema import AgentOpinion, EvidenceRecord

from agents import devops, devsecops, finops, pm_agent, sre

if TYPE_CHECKING:
    from app.services.llm_runtime import ActiveProvider


def run_all_agents(
    evidence: list[EvidenceRecord],
    llm_providers: list[ActiveProvider] | None = None,
) -> list[AgentOpinion]:
    return [
        devops.run(evidence, llm_providers=llm_providers),
        sre.run(evidence, llm_providers=llm_providers),
        finops.run(evidence, llm_providers=llm_providers),
        devsecops.run(evidence, llm_providers=llm_providers),
        pm_agent.run(evidence, llm_providers=llm_providers),
    ]
