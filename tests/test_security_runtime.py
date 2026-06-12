from __future__ import annotations

import pytest

from aaf.config import Settings, validate_runtime_safety


def test_validate_runtime_safety_allows_dev_defaults():
    s = Settings(app_env="dev")
    validate_runtime_safety(s)


def test_validate_runtime_safety_blocks_unsafe_prod():
    s = Settings(app_env="prod", jwt_secret="change-me-in-production-use-long-random-string")
    with pytest.raises(RuntimeError):
        validate_runtime_safety(s)


def test_validate_runtime_safety_blocks_public_metrics_in_prod():
    s = Settings(
        app_env="prod",
        jwt_secret="this-is-a-long-enough-secret-for-prod-tests-ok",
        superadmin_password="unique-superadmin-pass-xyz",
        admin_password="unique-admin-pass-xyz",
        app_encryption_key="very-strong-encryption-key-for-prod-tests",
        redis_url="redis://localhost:6379/0",
        cors_origins="https://app.example.com",
        public_tenant_signup_enabled=False,
        metrics_public_enabled=True,
    )
    with pytest.raises(RuntimeError, match="METRICS_PUBLIC"):
        validate_runtime_safety(s)


def _prod_safe_settings(**overrides) -> Settings:
    base = dict(
        app_env="prod",
        jwt_secret="this-is-a-long-enough-secret-for-prod-tests-ok",
        superadmin_password="unique-superadmin-pass-xyz",
        admin_password="unique-admin-pass-xyz",
        app_encryption_key="very-strong-encryption-key-for-prod-tests",
        redis_url="redis://localhost:6379/0",
        cors_origins="https://app.example.com",
        public_tenant_signup_enabled=False,
        metrics_public_enabled=False,
    )
    base.update(overrides)
    return Settings(**base)


def test_validate_runtime_safety_blocks_weak_encryption_key():
    s = _prod_safe_settings(app_encryption_key="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    with pytest.raises(RuntimeError, match="APP_ENCRYPTION_KEY"):
        validate_runtime_safety(s)


def test_validate_runtime_safety_requires_redis_in_prod():
    s = _prod_safe_settings(redis_url="", celery_broker_url="")
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        validate_runtime_safety(s)


def test_validate_runtime_safety_requires_cors_origins_in_prod():
    s = _prod_safe_settings(cors_origins="")
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        validate_runtime_safety(s)
