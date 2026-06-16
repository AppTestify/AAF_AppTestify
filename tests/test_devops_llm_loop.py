from __future__ import annotations

import pytest
from unittest.mock import patch

from aaf.config import Settings
from aaf.schema import RiskTheme, EvidenceRecord
from agents.devops import DevOpsAgent
from agents.schemas import EvidencePackage
from app.services.llm_runtime import ActiveProvider
from tools.context import build_tool_context


@pytest.mark.asyncio
async def test_devops_llm_loop_payments_release():
    settings = Settings(
        max_tool_calls_per_agent=5,
        connector_mode="sim",
    )
    
    agent = DevOpsAgent()
    ctx = build_tool_context(settings)
    ctx.evidence_package = {
        "tools": {},
        "records": []
    }
    
    records = [
        EvidenceRecord(
            source="github",
            kind="pull_request",
            summary="payments-service release PR",
            severity=0.5
        )
    ]
    package = EvidencePackage(
        records=records,
        prompt="Assess payments-service release readiness"
    )

    call_count = 0
    def mock_invoke_json(providers, prompt, system_prompt=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "thought": "I will check CI status for payments-service first.",
                "tool_name": "get_ci_status",
                "done": False
            }, {"model": "mock"}
        elif call_count == 2:
            return {
                "thought": "CI status shows a test step failure (0.40 pass). Now I will check for recent rollbacks.",
                "tool_name": "detect_rollbacks",
                "done": False
            }, {"model": "mock"}
        else:
            return {
                "thought": "2 rollbacks detected in 24h and test step failure. Confidence is high that there is operational risk.",
                "done": True,
                "claim": "payments-service release blocked due to test step failure and recent rollbacks.",
                "confidence": 0.87,
                "risk_theme": "operational_risk"
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

    assert "payments-service" in opinion.claim
    assert "test step failure" in opinion.claim
    assert opinion.confidence == 0.87
    assert opinion.risk_theme == RiskTheme.OPERATIONAL_RISK
    
    raw = opinion.raw_signals
    assert raw["tools_called"] == ["get_ci_status", "detect_rollbacks"]
    assert len(raw["tools_called"]) == 2
    
    skipped = raw["skipped_tools"]
    expected_skipped = [
        "get_deploy_history", 
        "check_branch_protection", 
        "get_pr_status", 
        "get_commit_activity", 
        "check_pipeline_config"
    ]
    for tool in expected_skipped:
        assert tool in skipped
    assert "get_ci_status" not in skipped
    assert "detect_rollbacks" not in skipped
    assert len(skipped) == 5
