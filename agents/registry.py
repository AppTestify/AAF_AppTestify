"""Run all domain agents on normalized evidence."""

from __future__ import annotations

from aaf.schema import AgentOpinion, EvidenceRecord

from agents import devops, devsecops, finops, pm_agent, sre


def run_all_agents(evidence: list[EvidenceRecord]) -> list[AgentOpinion]:
    return [
        devops.run(evidence),
        sre.run(evidence),
        finops.run(evidence),
        devsecops.run(evidence),
        pm_agent.run(evidence),
    ]
