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
        metrics_public_enabled=True,
    )
    with pytest.raises(RuntimeError, match="METRICS_PUBLIC"):
        validate_runtime_safety(s)
