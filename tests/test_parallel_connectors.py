import asyncio
import time
from unittest.mock import patch

import pytest

from aaf.config import Settings
from orchestrator.evidence import collect_evidence


@pytest.mark.asyncio
async def test_parallel_connectors_gather():
    settings = Settings(github_token="fake", jira_url="fake", openai_api_key="fake")
    
    async def mock_fetch_evidence(self, ctx):
        await asyncio.sleep(0.1)
        return {"mocked": True, "source": getattr(self, "name", "unknown")}
        
    with patch("connectors.github_connector.GitHubConnector.fetch_evidence", new=mock_fetch_evidence), \
         patch("connectors.jira_connector.JiraConnector.fetch_evidence", new=mock_fetch_evidence), \
         patch("connectors.finops_connector.FinopsConnector.fetch_evidence", new=mock_fetch_evidence):
         
        start_time = time.time()
        raw, normalized, evidence_package, tool_ctx = await collect_evidence(
            settings=settings,
            prompt="Test prompt",
            connector_names=["github", "jira", "finops"],
            ctx={},
            warm_tools=False
        )
        end_time = time.time()
        
        duration = end_time - start_time
        assert duration < 0.25, f"Expected parallel execution, took {duration:.2f}s"
        
        # Check evidence package metadata
        assert "run_id" in evidence_package
        assert evidence_package["run_id"] is not None
        assert "signal_count" in evidence_package
        assert evidence_package["signal_count"] == len(normalized)
        assert "staleness_summary" in evidence_package
        
        # Check that we received results from all connectors
        assert "github" in raw
        assert "jira" in raw
        assert "finops" in raw
