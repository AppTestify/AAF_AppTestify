from aaf.schema import AgentOpinion, RiskTheme


def test_agent_opinion_defaults():
    o = AgentOpinion(
        agent_id="devops",
        claim="Tests failing",
        confidence=0.8,
        risk_theme=RiskTheme.OPERATIONAL_RISK,
    )
    assert o.confidence == 0.8
