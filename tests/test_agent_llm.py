import pytest
from aaf.config import ConnectorMode
from aaf.schema import EvidenceRecord, RiskTheme
from tools.context import build_tool_context
from agents import devops, finops, devsecops, pm_agent


def test_agents_tool_weighted_mode(settings):
    settings.connector_mode = ConnectorMode.SIM
    tool_ctx = build_tool_context(settings)
    evidence = [
        EvidenceRecord(source="github", kind="workflow_fail", summary="CI workflow failed on main", severity=0.8),
        EvidenceRecord(source="jira", kind="overdue_task", summary="Sprint issue is overdue", severity=0.7),
        EvidenceRecord(source="finops", kind="cost_anomaly", summary="Unusual cost spike detected", severity=0.9),
    ]

    op_devops = devops.run(evidence, llm_providers=None, tool_ctx=tool_ctx)
    assert op_devops.agent_id == "devops"
    assert op_devops.confidence > 0
    assert len(op_devops.evidence) > 0
    assert "get_ci_status" in op_devops.raw_signals

    op_finops = finops.run(evidence, llm_providers=None, tool_ctx=tool_ctx)
    assert op_finops.agent_id == "finops"
    assert op_finops.risk_theme == RiskTheme.COST_RISK
    assert "Ci" in op_finops.raw_signals

    op_pm = pm_agent.run(evidence, llm_providers=None, tool_ctx=tool_ctx)
    assert op_pm.agent_id == "project_management"
    assert op_pm.confidence > 0

    op_sec = devsecops.run(evidence, llm_providers=None, tool_ctx=tool_ctx)
    assert op_sec.agent_id == "devsecops"


@pytest.mark.asyncio
async def test_run_all_agents_parallel(settings):
    from agents.registry import run_all_agents_async

    settings.connector_mode = ConnectorMode.SIM
    ctx = build_tool_context(settings)
    evidence = [
        EvidenceRecord(source="github", kind="workflow_fail", summary="CI failed", severity=0.8),
    ]
    opinions = await run_all_agents_async(evidence, tool_ctx=ctx, settings=settings)
    assert len(opinions) == 4
    ids = {o.agent_id for o in opinions}
    assert ids == {"devops", "finops", "devsecops", "project_management"}


def test_utility_global_formula(settings):
    from aaf.schema import AgentOpinion
    from orchestrator.utility import score_actions

    evidence = [EvidenceRecord(source="finops", kind="cost_anomaly", summary="spike", severity=0.8)]
    opinions = [
        AgentOpinion(
            agent_id="finops",
            claim="Cost risk",
            confidence=0.7,
            raw_signals={"Ci": 0.4},
            risk_theme=RiskTheme.COST_RISK,
        )
    ]
    result = score_actions(evidence, settings, opinions=opinions)
    assert result.cost_index == 0.4
    assert result.global_utility == pytest.approx(0.4 * 0.3 + result.perf_index * 0.4 + result.risk_index * 0.3, rel=0.1)
