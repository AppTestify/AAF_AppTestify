"""Tool registry API tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_tool_registry_returns_all_entries():
    with TestClient(app) as client:
        r = client.get("/api/v1/agents/tool-registry")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total_count"] == 31
    assert body["meta"]["shipped_count"] == 31
    assert body["meta"]["roadmap_count"] == 0
    assert len(body["agents"]) == 4


def test_tool_registry_filter_by_agent():
    with TestClient(app) as client:
        r = client.get("/api/v1/agents/tool-registry?agent=devops")
    assert r.status_code == 200
    body = r.json()
    assert len(body["agents"]) == 1
    assert body["agents"][0]["id"] == "devops"
    assert all(t["agent_id"] == "devops" for t in body["agents"][0]["tools"])


def test_tool_registry_filter_shipped_only():
    with TestClient(app) as client:
        r = client.get("/api/v1/agents/tool-registry?status=shipped")
    assert r.status_code == 200
    body = r.json()
    for section in body["agents"]:
        for tool in section["tools"]:
            assert tool["implementation_status"] == "shipped"
