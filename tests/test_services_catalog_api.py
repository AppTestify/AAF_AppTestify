from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.conftest_auth import cookie_client, login_as


@pytest.fixture
def client(cookie_client):
    return cookie_client


def test_services_catalog_crud(client: TestClient):
    login_as(client, "admin@example.com", "test-password-123")

    # Create portfolio project to link (optional but good practice)
    project = client.post(
        "/api/v1/portfolio/projects",
        json={"key": "SVCPROJ", "name": "Service Project", "owner": "DevOps", "status": "active"},
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    # 1. Create a service (POST)
    payload = {
        "name": "AuthService",
        "owner": "Security Team",
        "tier": "tier1",
        "repo_url": "https://github.com/example/auth-service",
        "slo_json": {"availability": 99.9, "latency_p95_ms": 150},
        "dependencies_json": ["db-primary", "cache-redis"],
        "portfolio_project_id": project_id,
    }
    create_resp = client.post("/api/v1/services", json=payload)
    assert create_resp.status_code == 201, create_resp.text
    service = create_resp.json()
    assert service["name"] == "AuthService"
    assert service["owner"] == "Security Team"
    assert service["tier"] == "tier1"
    assert service["slo_json"] == {"availability": 99.9, "latency_p95_ms": 150}
    assert service["dependencies_json"] == ["db-primary", "cache-redis"]
    assert service["portfolio_project_id"] == project_id
    service_id = service["id"]

    # 2. Get a specific service (GET /{id})
    get_resp = client.get(f"/api/v1/services/{service_id}")
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["name"] == "AuthService"

    # 3. List services (GET)
    list_resp = client.get("/api/v1/services")
    assert list_resp.status_code == 200, list_resp.text
    services = list_resp.json()
    assert len(services) >= 1
    assert any(s["id"] == service_id for s in services)

    # 4. Update the service (PUT)
    update_payload = {
        "name": "AuthService-v2",
        "owner": "Platform Team",
        "tier": "tier0",
        "repo_url": "https://github.com/example/auth-service-v2",
        "slo_json": {"availability": 99.99, "latency_p95_ms": 100},
        "dependencies_json": ["db-primary", "cache-redis", "queue-rabbitmq"],
        "portfolio_project_id": project_id,
    }
    update_resp = client.put(f"/api/v1/services/{service_id}", json=update_payload)
    assert update_resp.status_code == 200, update_resp.text
    updated_service = update_resp.json()
    assert updated_service["name"] == "AuthService-v2"
    assert updated_service["owner"] == "Platform Team"
    assert updated_service["tier"] == "tier0"
    assert updated_service["slo_json"] == {"availability": 99.99, "latency_p95_ms": 100}
    assert updated_service["dependencies_json"] == ["db-primary", "cache-redis", "queue-rabbitmq"]

    # 5. Delete the service (DELETE)
    delete_resp = client.delete(f"/api/v1/services/{service_id}")
    assert delete_resp.status_code == 204, delete_resp.text

    # 6. Verify deletion (GET /{id} -> 404)
    get_deleted_resp = client.get(f"/api/v1/services/{service_id}")
    assert get_deleted_resp.status_code == 404, get_deleted_resp.text
