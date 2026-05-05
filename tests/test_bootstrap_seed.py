"""Optional test tenant seeding."""

from __future__ import annotations

import pytest
from sqlalchemy import select


@pytest.fixture
def seed_db(monkeypatch, tmp_path):
    db_path = tmp_path / "seed_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret-key-min-32-chars!!")
    monkeypatch.setenv("SUPERADMIN_EMAIL", "super@example.com")
    monkeypatch.setenv("SUPERADMIN_PASSWORD", "super-pass-123")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password-123")
    monkeypatch.setenv("SEED_TEST_TENANT", "true")
    monkeypatch.setenv("TEST_TENANT_SLUG", "test")
    monkeypatch.setenv("TEST_TENANT_ADMIN_EMAIL", "testadmin@example.org")
    monkeypatch.setenv("TEST_TENANT_ADMIN_PASSWORD", "test-tenant-pass-123")

    from app import deps

    deps.settings_dep.cache_clear()

    from aaf.config import get_settings
    from app import db as db_mod
    from app.bootstrap import create_tables, bootstrap_tenancy

    settings = get_settings()
    db_mod.init_db(settings.database_url)
    create_tables()
    db = db_mod.SessionLocal()
    try:
        bootstrap_tenancy(db, settings)
    finally:
        db.close()

    yield settings

    deps.settings_dep.cache_clear()


def test_seed_creates_test_tenant_and_admin(seed_db):
    from app import db as db_mod
    from app.models.tenant import Tenant
    from app.models.user import User

    settings = seed_db
    db = db_mod.SessionLocal()
    try:
        tenant = db.execute(select(Tenant).where(Tenant.slug == "test")).scalar_one()
        assert tenant.name
        user = db.execute(select(User).where(User.email == "testadmin@example.org")).scalar_one()
        assert user.tenant_id == tenant.id
        assert user.is_admin is True
        assert user.is_superadmin is False
    finally:
        db.close()

    assert settings.superadmin_email == "super@example.com"
