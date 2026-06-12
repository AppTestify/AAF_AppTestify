"""Optional live connector health checks — run only when CONNECTOR_LIVE_CI=1."""

from __future__ import annotations

import os

import pytest

from aaf.config import ConnectorMode, get_settings
from connectors.github_connector import GitHubConnector
from connectors.jira_connector import JiraConnector


pytestmark = pytest.mark.live_connector


def _live_enabled() -> bool:
    return os.getenv("CONNECTOR_LIVE_CI") == "1"


@pytest.mark.asyncio
async def test_github_connector_live_health(monkeypatch):
    if not _live_enabled():
        pytest.skip("CONNECTOR_LIVE_CI not set")
    token = os.getenv("GITHUB_TOKEN", "").strip()
    repo = os.getenv("GITHUB_REPO", "").strip()
    if not token or not repo:
        pytest.skip("GITHUB_TOKEN and GITHUB_REPO required for live connector test")

    monkeypatch.setenv("CONNECTOR_MODE", ConnectorMode.LIVE.value)
    monkeypatch.setenv("GITHUB_TOKEN", token)
    monkeypatch.setenv("GITHUB_REPO", repo)
    from app import deps

    deps.settings_dep.cache_clear()
    settings = get_settings()
    connector = GitHubConnector(settings)
    payload = await connector.fetch_evidence({"github_repo": repo})
    assert payload.get("simulated") is False
    assert "error" not in payload or payload.get("pull_requests") is not None
    deps.settings_dep.cache_clear()


@pytest.mark.asyncio
async def test_jira_connector_live_health(monkeypatch):
    if not _live_enabled():
        pytest.skip("CONNECTOR_LIVE_CI not set")
    url = os.getenv("JIRA_URL", "").strip()
    email = os.getenv("JIRA_EMAIL", "").strip()
    api_token = os.getenv("JIRA_API_TOKEN", "").strip()
    project = os.getenv("JIRA_PROJECT", "").strip()
    if not all([url, email, api_token, project]):
        pytest.skip("JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT required")

    monkeypatch.setenv("CONNECTOR_MODE", ConnectorMode.LIVE.value)
    monkeypatch.setenv("JIRA_URL", url)
    monkeypatch.setenv("JIRA_EMAIL", email)
    monkeypatch.setenv("JIRA_API_TOKEN", api_token)
    monkeypatch.setenv("JIRA_PROJECT", project)
    from app import deps

    deps.settings_dep.cache_clear()
    settings = get_settings()
    connector = JiraConnector(settings)
    payload = await connector.fetch_evidence({"jira_project": project})
    assert payload.get("simulated") is False
    deps.settings_dep.cache_clear()
