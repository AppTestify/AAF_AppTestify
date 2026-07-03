from __future__ import annotations

import pytest
from unittest.mock import patch

from aaf.config import Settings
from aaf.schema import RiskTheme, EvidenceRecord
from agents.finops import FinOpsAgent
from agents.schemas import EvidencePackage
from app.services.llm_runtime import ActiveProvider
from tools.context import build_tool_context


@pytest.mark.asyncio
async def test_finops_llm_loop_scaling_misconfig():
    settings = Settings(
        max_tool_calls_per_agent=5,
        connector_mode="sim",
    )
    
    agent = FinOpsAgent()
    ctx = build_tool_context(settings)
    ctx.evidence_package = {
        "tools": {},
        "records": []
    }
    
    # Evidence representing a cost anomaly narrative
    records = [
        EvidenceRecord(
            source="aws_billing",
            kind="cost_anomaly",
            summary="Unusual spending increase observed in compute resources",
            severity=0.8
        )
    ]
    package = EvidencePackage(
        records=records,
        prompt="Assess cloud cost risks"
    )

    call_count = 0
    def mock_invoke_json(providers, prompt, system_prompt=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "thought": "I should start by checking the overall spend trend to quantify the anomaly.",
                "tool_name": "get_spend_trend",
                "done": False
            }, {"model": "mock"}
        elif call_count == 2:
            return {
                "thought": "Spend trend shows a +44% WoW increase. Let's check for specific scaling anomalies.",
                "tool_name": "detect_scaling_anomaly",
                "done": False
            }, {"model": "mock"}
        else:
            return {
                "thought": "Scaling anomaly found: orphan_scale with 47 instances. This explains the +44% WoW trend. Skipping budget and RI tools as root cause is confirmed.",
                "done": True,
                "claim": "Cost risk is elevated due to +44% WoW spend trend caused by an orphan_scale anomaly affecting 47 instances.",
                "confidence": 0.79,
                "risk_theme": "cost_risk"
            }, {"model": "mock"}

    mock_providers = [
        ActiveProvider(
            provider_name="mock",
            model_name="mock",
            endpoint_url=None,
            temperature=None,
            max_tokens=None,
            timeout_seconds=5,
            api_key="test",
            metadata_json={}
        )
    ]

    with patch("agents.llm_tool_loop.invoke_json_with_failover", side_effect=mock_invoke_json):
        opinion = await agent.run_llm_loop(
            ctx=ctx,
            package=package,
            llm_providers=mock_providers,
            settings=settings,
        )

    assert opinion.confidence == 0.79
    assert opinion.risk_theme == RiskTheme.COST_RISK
    assert "+44% WoW" in opinion.claim
    assert "orphan_scale" in opinion.claim
    assert "47 instances" in opinion.claim
    
    raw = opinion.raw_signals
    # 2 tools called
    assert raw["tools_called"] == ["get_spend_trend", "detect_scaling_anomaly"]
    assert len(raw["tools_called"]) == 2
    
    skipped = raw["skipped_tools"]
    expected_skipped = [
        "check_budget_pace", 
        "calc_unit_cost", 
        "get_ri_coverage", 
        "get_cost_by_tag", 
        "get_cost_forecast"
    ]
    for tool in expected_skipped:
        assert tool in skipped
    
    assert "get_spend_trend" not in skipped
    assert "detect_scaling_anomaly" not in skipped
    
    # Check that budget and RI tools were skipped
    assert "check_budget_pace" in skipped
    assert "get_ri_coverage" in skipped
    assert len(skipped) == 5
