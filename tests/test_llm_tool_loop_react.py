from __future__ import annotations

import pytest
from unittest.mock import patch

from aaf.config import Settings
from aaf.schema import RiskTheme
from agents.devops import DevOpsAgent
from agents.schemas import EvidencePackage
from agents.llm_tool_loop import run_llm_tool_loop
from app.services.llm_runtime import ActiveProvider
from tools.context import build_tool_context


@pytest.mark.asyncio
async def test_react_loop_runs_two_tools_then_stops():
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
    
    package = EvidencePackage(
        records=[],
        prompt="Should we release?"
    )

    call_count = 0
    def mock_invoke_json(providers, prompt, system_prompt=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "thought": "I need to check the CI build status first.",
                "tool_name": "get_ci_status",
                "done": False
            }, {"model": "mock"}
        elif call_count == 2:
            return {
                "thought": "CI status is green. Now checking branch protection rules.",
                "tool_name": "check_branch_protection",
                "done": False
            }, {"model": "mock"}
        else:
            return {
                "thought": "Branch protection looks solid and CI is passing. We are safe.",
                "done": True,
                "claim": "Build is safe to release based on CI and branch protection.",
                "confidence": 0.92,
                "risk_theme": "low_risk"
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
        opinion = await run_llm_tool_loop(
            agent=agent,
            ctx=ctx,
            package=package,
            llm_providers=mock_providers,
            settings=settings,
        )

    # Assertions
    assert opinion.claim == "Build is safe to release based on CI and branch protection."
    assert opinion.confidence == 0.92
    assert opinion.risk_theme == RiskTheme.LOW_RISK
    
    raw = opinion.raw_signals
    assert raw["tools_called"] == ["get_ci_status", "check_branch_protection"]
    assert "get_ci_status" not in raw["skipped_tools"]
    assert "check_branch_protection" not in raw["skipped_tools"]
    assert "detect_rollbacks" in raw["skipped_tools"]
    assert "detect_rollbacks" in raw["tools_skipped"]
    
    steps = raw["reasoning_steps"]
    assert len(steps) == 3
    assert steps[0]["thought"] == "I need to check the CI build status first."
    assert steps[0]["tool_called"] == "get_ci_status"
    assert steps[0]["done"] is False
    
    assert steps[1]["thought"] == "CI status is green. Now checking branch protection rules."
    assert steps[1]["tool_called"] == "check_branch_protection"
    assert steps[1]["done"] is False
    
    assert steps[2]["thought"] == "Branch protection looks solid and CI is passing. We are safe."
    assert steps[2]["done"] is True
    assert steps[2]["claim"] == "Build is safe to release based on CI and branch protection."
    assert steps[2]["confidence"] == 0.92
