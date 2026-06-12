"""Shared Redis client for production middleware and rate limiting."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

import redis

from aaf.config import get_settings


@lru_cache(maxsize=1)
def get_redis_client() -> Optional[redis.Redis]:
    settings = get_settings()
    url = settings.redis_url or settings.celery_broker_url
    if not url:
        return None
    return redis.Redis.from_url(url, decode_responses=True)
