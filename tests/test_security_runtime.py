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
