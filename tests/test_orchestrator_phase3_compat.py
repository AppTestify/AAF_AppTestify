import pytest

from aaf.config import Settings
from aaf.schema import AgentOpinion, RiskTheme
from orchestrator.consensus import compute_consensus_phase1, compute_consensus
from orchestrator.utility import score_actions


def test_phase3_agent_opinion_pydantic_validation():
    # Phase 3 opinions include rich raw_signals like reasoning_steps, tools_called, etc.
    op = AgentOpinion(
        agent_id="devops",
        display_id="DevOps",
        claim="Cost risk is elevated",
        confidence=0.87,
        evidence=["mock"],
        evidence_refs=["devops:mock"],
        risk_theme=RiskTheme.OPERATIONAL_RISK,
        raw_signals={
            "tools_called": ["get_ci_status", "detect_rollbacks"],
            "skipped_tools": ["check_branch_protection"],
            "reasoning_steps": [{"step": 1, "thought": "check CI", "tool_called": "get_ci_status", "done": False}],
            "transport": "mcp"
        }
    )
    assert op.agent_id == "devops"
    assert op.confidence == 0.87
    assert op.risk_theme == RiskTheme.OPERATIONAL_RISK


def test_orchestrator_payments_fixture_compat():
    op1 = AgentOpinion(
        agent_id="devops",
        claim="Devops risk",
        confidence=0.87,
        risk_theme=RiskTheme.OPERATIONAL_RISK,
        raw_signals={"tools_called": ["get_ci_status", "detect_rollbacks"]}
    )
    op2 = AgentOpinion(
        agent_id="pm",
        claim="Delivery risk",
        confidence=0.82,
        risk_theme=RiskTheme.DELIVERY_RISK,
        raw_signals={"tools_called": ["count_blockers", "get_open_defects"]}
    )
    op3 = AgentOpinion(
        agent_id="finops",
        claim="Cost risk",
        confidence=0.79,
        risk_theme=RiskTheme.COST_RISK,
        raw_signals={"tools_called": ["get_spend_trend", "detect_scaling_anomaly"]}
    )

    opinions = [op1, op2, op3]
    
    # Phase 1 consensus
    c1 = compute_consensus_phase1(opinions)
    assert c1.consensus_score > 0
    
    # Phase 3 consensus
    c3 = compute_consensus(opinions)
    assert c3.consensus_score > 0
    
    # Utility scoring
    settings = Settings()
    result = score_actions([], settings, opinions=opinions)
    assert result.global_utility > 0
    # Average confidence is > 0.79, HOLD_RELEASE should beat MITIGATE_MONITOR
    from aaf.schema import GovernanceAction
    assert result.recommended_action == GovernanceAction.HOLD_RELEASE
    assert result.utility_score > result.scores_by_action.get(GovernanceAction.MITIGATE_MONITOR.value, 0.0)


def test_phase1_static_opinions_regression():
    # Phase 1 static opinions without rich tool data
    op = AgentOpinion(
        agent_id="security",
        claim="Secure",
        confidence=0.99,
        risk_theme=RiskTheme.LOW_RISK,
        raw_signals={}
    )
    
    opinions = [op]
    c1 = compute_consensus_phase1(opinions)
    assert c1.consensus_score == 0.995 # 0.5 * 0.99 + 0.5 * 1.0
    
    c3 = compute_consensus(opinions)
    assert c3.consensus_score == 1.0 # 0.7 * 1.0 + 0.3 * 1.0
