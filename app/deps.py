from __future__ import annotations

from functools import lru_cache

from aaf.config import Settings, get_settings


@lru_cache
def settings_dep() -> Settings:
    return get_settings()
