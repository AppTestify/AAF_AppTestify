"""Unit tests for the GitLab connector, normalizer, and settings integration."""

from __future__ import annotations

import httpx
import pytest
from unittest.mock import MagicMock

from aaf.config import ConnectorMode, Settings
from aaf.schema import EvidenceRecord, GovernanceAction
from app.models.config import TenantConnectorConfig
from app.services.config_resolver import resolve_effective_settings
from connectors.evidence_normalizer import normalize_all, _gitlab
from connectors.gitlab_connector import GitLabConnector


class _SettingsStub:
    connector_mode = ConnectorMode.SIM
    fixtures_dir = Settings().fixtures_dir
    gitlab_token = ""
    gitlab_project_id = ""
    gitlab_url = "https://gitlab.com"


@pytest.mark.asyncio
async def test_gitlab_connector_sim_mode():
    conn = GitLabConnector(_SettingsStub())
    ctx = {}
    res = await conn.fetch_evidence(ctx)
    assert res.get("simulated") is True
    assert "merge_requests" in res
    assert "pipelines" in res
    assert "issues" in res


def test_gitlab_normalizer_mapping():
    payload = {
        "project_id": "test-group/test-proj",
        "merge_requests": [
            {"id": 10, "iid": 1, "title": "feat: cool feature", "state": "opened", "work_in_progress": False, "web_url": "https://gitlab.com/mr/1"},
            {"id": 11, "iid": 2, "title": "Draft: broken check", "state": "opened", "draft": True, "web_url": "https://gitlab.com/mr/2"},
            {"id": 12, "iid": 3, "title": "wip: block release", "state": "opened", "work_in_progress": True, "web_url": "https://gitlab.com/mr/3"},
            {"id": 13, "iid": 4, "title": "merged mr", "state": "merged", "work_in_progress": False}
        ],
        "pipelines": [
            {"id": 100, "status": "success", "web_url": "https://gitlab.com/pipe/100"},
            {"id": 101, "status": "failed", "web_url": "https://gitlab.com/pipe/101"},
            {"id": 102, "status": "canceled", "web_url": "https://gitlab.com/pipe/102"}
        ],
        "issues": [
            {"id": 200, "iid": 10, "title": "normal issue", "state": "opened", "labels": ["docs"], "web_url": "https://gitlab.com/issue/200"},
            {"id": 201, "iid": 11, "title": "critical bug", "state": "opened", "labels": ["bug", "high"], "web_url": "https://gitlab.com/issue/201"},
            {"id": 202, "iid": 12, "title": "closed issue", "state": "closed", "labels": ["bug"]}
        ]
    }
    
    records = _gitlab(payload)
    
    # Verify MRs
    open_mrs = [r for r in records if r.kind == "open_mr"]
    assert len(open_mrs) == 3
    # Normal MR
    assert open_mrs[0].severity == 0.25
    assert open_mrs[0].metadata["iid"] == 1
    # Draft MR
    assert open_mrs[1].severity == 0.35
    # WIP MR with block in title
    assert open_mrs[2].severity == 0.45  # 0.35 + 0.1
    
    # Verify Pipelines
    pipelines = [r for r in records if r.kind == "pipeline"]
    assert len(pipelines) == 3
    assert pipelines[0].severity == 0.15  # success
    assert pipelines[1].severity == 0.85  # failed
    assert pipelines[2].severity == 0.5   # canceled
    
    # Verify Issues
    open_issues = [r for r in records if r.kind == "open_issue"]
    assert len(open_issues) == 2
    assert open_issues[0].severity == 0.4   # normal
    assert open_issues[1].severity == 0.65  # bug


def test_gitlab_config_resolver():
    base = Settings()
    tenant = MagicMock()
    tenant.id = 123
    
    config_row = TenantConnectorConfig(
        tenant_id=123,
        connector_name="gitlab",
        enabled=True,
        config_json={"gitlab_url": "https://my-gitlab.org", "project_id": "999"},
        encrypted_credentials_json=None
    )
    
    # Mock decrypt_json to return credentials
    # Since we can just mock config_resolver or return stub list of rows
    # Let's mock the DB query in config_resolver
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [config_row]
    
    effective = resolve_effective_settings(db, base, tenant)
    assert effective.connector_mode == ConnectorMode.LIVE
    assert effective.gitlab_url == "https://my-gitlab.org"
    assert effective.gitlab_project_id == "999"


@pytest.mark.asyncio
async def test_fetch_gitlab_signal_live(monkeypatch):
    from app.services.gitlab_live import fetch_gitlab_signal

    # Mock HTTP client responses
    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_get_json_with_retry(client, url):
        if url.endswith("/pipelines?per_page=20"):
            return [{"id": 1, "status": "success"}, {"id": 2, "status": "failed"}]
        elif url.endswith("/merge_requests?state=opened&per_page=20"):
            return [{"id": 10}]
        elif url.endswith("/issues?state=opened&per_page=20"):
            return [{"id": 100}, {"id": 101}]
        elif "/projects/" in url:
            return {"id": 99, "name": "my-project"}
        return None

    monkeypatch.setattr("httpx.Client", MockClient)
    monkeypatch.setattr("app.services.gitlab_live.get_json_with_retry", mock_get_json_with_retry)

    res = fetch_gitlab_signal("test-project", token="my-token")
    assert res["connector"] == "gitlab"
    assert res["mode"] == "live"
    assert res["open_merge_requests"] == 1
    assert res["open_issues"] == 2
    assert res["failing_pipelines"] == 1
    assert res["success_rate"] == 0.5
