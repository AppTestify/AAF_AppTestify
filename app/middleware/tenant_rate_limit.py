"""Per-tenant governance run rate limiting (Redis-backed when configured)."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.redis_client import get_redis_client

_log = logging.getLogger(__name__)

_RUN_LIMIT_PER_HOUR = 100
_window_seconds = 3600
_buckets: dict[str, deque[float]] = defaultdict(deque)


def _memory_rate_limited(tenant_key: str, now: float) -> tuple[bool, int]:
    bucket = _buckets[tenant_key]
    while bucket and now - bucket[0] > _window_seconds:
        bucket.popleft()
    if len(bucket) >= _RUN_LIMIT_PER_HOUR:
        retry_after = int(_window_seconds - (now - bucket[0])) if bucket else _window_seconds
        return True, max(1, retry_after)
    bucket.append(now)
    return False, 0


def _redis_rate_limited(tenant_key: str, now: float) -> tuple[bool, int]:
    client = get_redis_client()
    if client is None:
        return _memory_rate_limited(tenant_key, now)

    key = f"aaf:rate:governance_runs:{tenant_key}"
    try:
        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, now - _window_seconds)
        pipe.zcard(key)
        count, current = pipe.execute()
        if current >= _RUN_LIMIT_PER_HOUR:
            oldest = client.zrange(key, 0, 0, withscores=True)
            retry_after = _window_seconds
            if oldest:
                retry_after = int(_window_seconds - (now - float(oldest[0][1])))
            return True, max(1, retry_after)
        pipe = client.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, _window_seconds)
        pipe.execute()
        return False, 0
    except Exception:  # noqa: BLE001
        _log.exception("redis_rate_limit_failed", extra={"tenant_key": tenant_key})
        return _memory_rate_limited(tenant_key, now)


class TenantRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if request.method == "POST" and path.rstrip("/").endswith("/governance/runs"):
            tenant_key = request.query_params.get("tenant_slug") or request.headers.get("x-tenant-slug") or "default"
            now = time.time()
            limited, retry_after = _redis_rate_limited(tenant_key, now)
            if limited:
                return Response(
                    content='{"detail":"Rate limit exceeded"}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)
