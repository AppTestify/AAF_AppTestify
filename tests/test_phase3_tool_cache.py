from __future__ import annotations

import pytest
from unittest.mock import patch

from aaf.config import Settings
from orchestrator.evidence import collect_evidence
from orchestrator.pipeline import run_pipeline
from tools.context import get_cached_tool_result


@pytest.mark.asyncio
async def test_phase3_tool_caching_and_bypass():
    settings = Settings(
        pipeline_phase=3,
        connector_mode="sim",
        rar_live_refresh_enabled=False,
    )
    
    # 1. Warm the cache by running collect_evidence
    raw, normalized, package, tool_ctx = await collect_evidence(
        settings=settings,
        prompt="Should we release?",
        connector_names=["github", "jira"],
        ctx={"prompt": "Should we release?", "github_repo": settings.github_repo, "jira_project": settings.jira_project},
        warm_tools=True,
    )
    
    assert "get_ci_status" in package["tools"]
    assert "count_blockers" in package["tools"]

    # 2. Mock github_get and jira_get to raise an error if called
    def fail_on_http(*args, **kwargs):
        raise AssertionError("HTTP API call detected during agent execution!")

    with patch("tools.github_client.github_get", side_effect=fail_on_http), \
         patch("tools.jira_client.jira_get", side_effect=fail_on_http):
         
        # Run the pipeline under Phase 3.
        # Since all tools are cached, this should complete successfully without raising AssertionError.
        res = await run_pipeline(
            prompt="Should we release?",
            prompt_id="test-run",
            settings=settings,
            normalized_evidence=normalized,
            raw_evidence_by_connector=raw,
            connectors_used=["github", "jira"],
            tool_ctx=tool_ctx,
            evidence_package=package,
        )
        assert res.consensus.consensus_score >= 0.0

    # 3. Verify that refresh_tools correctly bypasses the cache
    # If we request a refresh for a tool, it should bypass the cache and try to make an API call (which will trigger our mock)
    called_mock = False
    def mark_called(*args, **kwargs):
        nonlocal called_mock
        called_mock = True
        return None  # return None to simulate empty API response

    # Set connector mode to live temporarily so the tool does not short-circuit to sim data
    old_mode = tool_ctx.settings.connector_mode
    tool_ctx.settings.connector_mode = "live"
    try:
        with patch("tools.devops.ci_status.github_get", side_effect=mark_called):
            # We run DevOpsAgent's tools requesting refresh of 'get_ci_status'
            from agents.devops import DevOpsAgent
            agent = DevOpsAgent()
            
            # When running tools with refresh_tools=['get_ci_status'], it should bypass the cache
            # and hit our mock.
            await agent.run_tools(tool_ctx, refresh_tools=["get_ci_status"])
            assert called_mock, "Expected github_get to be called when refreshing get_ci_status"
    finally:
        tool_ctx.settings.connector_mode = old_mode
