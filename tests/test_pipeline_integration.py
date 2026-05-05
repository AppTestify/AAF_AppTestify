import pytest

from aaf.config import Settings
from app.services.governance_service import run_governance


@pytest.mark.asyncio
async def test_governance_run_sim():
    settings = Settings(
        tau_consensus=0.99,
        max_rar_loops=1,
    )
    r = await run_governance("GitHub cost JIRA sprint review", None, settings)
    assert r.consensus.consensus_score >= 0.0
    assert r.utility.recommended_action
    assert r.explanation
    assert "github" in r.connectors_used or "jira" in r.connectors_used
