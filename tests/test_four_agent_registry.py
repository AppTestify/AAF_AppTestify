import asyncio

from aaf.schema import EvidenceRecord
from agents.registry import run_agents_async, run_all_agents_async


def test_four_agents_dispatch():
    evidence = [
        EvidenceRecord(source="github", kind="ci", summary="CI failed on main", severity=0.7),
        EvidenceRecord(source="jira", kind="sprint", summary="3 blockers open", severity=0.6),
    ]
    opinions = asyncio.run(run_all_agents_async(evidence))
    assert len(opinions) == 4
    agent_ids = {o.agent_id for o in opinions}
    assert agent_ids == {"devops", "finops", "devsecops", "project_management"}


def test_selective_agents_dispatch():
    evidence = [
        EvidenceRecord(source="github", kind="ci", summary="CI failed on main", severity=0.7),
    ]
    opinions = asyncio.run(
        run_agents_async(evidence, ["devops", "project_management", "finops"])
    )
    assert len(opinions) == 3
    agent_ids = {o.agent_id for o in opinions}
    assert "devsecops" not in agent_ids
    assert agent_ids == {"devops", "finops", "project_management"}
