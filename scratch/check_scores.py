from aaf.schema import AgentOpinion, RiskTheme
from aaf.config import Settings
from orchestrator.utility import score_actions

op1 = AgentOpinion(
    agent_id="devops",
    claim="Devops risk",
    confidence=0.87,
    risk_theme=RiskTheme.OPERATIONAL_RISK,
    raw_signals={}
)
op2 = AgentOpinion(
    agent_id="pm",
    claim="Delivery risk",
    confidence=0.82,
    risk_theme=RiskTheme.DELIVERY_RISK,
    raw_signals={}
)
op3 = AgentOpinion(
    agent_id="finops",
    claim="Cost risk",
    confidence=0.79,
    risk_theme=RiskTheme.COST_RISK,
    raw_signals={}
)

opinions = [op1, op2, op3]
settings = Settings()
result = score_actions([], settings, opinions=opinions)
print("Recommended:", result.recommended_action)
print("Scores:")
for k, v in result.scores_by_action.items():
    print(f"  {k}: {v}")
