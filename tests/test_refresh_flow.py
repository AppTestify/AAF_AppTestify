import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "auth_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret-key-min-32-chars!!")
    monkeypatch.setenv("SUPERADMIN_EMAIL", "super@example.com")
    monkeypatch.setenv("SUPERADMIN_PASSWORD", "super-pass-123")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password-123")
    
    from app import deps
    deps.settings_dep.cache_clear()
    
    from app.main import app
    with TestClient(app, base_url="https://testserver") as c:
        yield c
        
    deps.settings_dep.cache_clear()
    app.dependency_overrides.clear()


def test_login_sets_refresh_token_cookie(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    assert r.status_code == 200
    assert "access_token" in r.cookies
    assert "refresh_token" in r.cookies


def test_refresh_token_success(client):
    # 1. Login to get cookies
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    assert r.status_code == 200
    
    access_token_1 = r.cookies.get("access_token")
    refresh_token = r.cookies.get("refresh_token")
    
    # 2. Clear access_token cookie to simulate expiration
    if "access_token" in client.cookies:
        del client.cookies["access_token"]
    
    import time
    time.sleep(1.1)
    
    # 3. Call refresh endpoint
    r_refresh = client.post("/api/v1/auth/refresh")
    assert r_refresh.status_code == 200, r_refresh.text
    
    access_token_2 = r_refresh.cookies.get("access_token")
    assert access_token_2 is not None
    assert access_token_2 != access_token_1
    # Check that refresh token is still present
    assert client.cookies.get("refresh_token") == refresh_token


def test_refresh_token_invalid_or_expired(client):
    # Call refresh without a cookie
    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 401
    
    # Call refresh with an invalid cookie
    client.cookies.set("refresh_token", "invalid-token-value")
    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 401


def test_logout_revokes_refresh_token(client):
    # 1. Login
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    assert r.status_code == 200
    assert "refresh_token" in r.cookies
    
    # 2. Logout
    r_logout = client.post("/api/v1/auth/logout")
    assert r_logout.status_code == 200
    
    # 3. Cookies should be deleted
    assert r_logout.cookies.get("access_token") == "" or r_logout.cookies.get("access_token") is None
    assert r_logout.cookies.get("refresh_token") == "" or r_logout.cookies.get("refresh_token") is None
    
    # 4. Trying to refresh should fail (since it was deleted/revoked from DB)
    r_refresh = client.post("/api/v1/auth/refresh")
    assert r_refresh.status_code == 401
