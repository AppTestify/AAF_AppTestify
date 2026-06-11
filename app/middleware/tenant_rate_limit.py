"""Per-tenant governance run rate limiting."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

_RUN_LIMIT_PER_HOUR = 100
_window_seconds = 3600
_buckets: dict[str, deque[float]] = defaultdict(deque)


class TenantRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/governance/runs"):
            tenant_key = request.headers.get("x-tenant-slug") or "default"
            now = time.time()
            bucket = _buckets[tenant_key]
            while bucket and now - bucket[0] > _window_seconds:
                bucket.popleft()
            if len(bucket) >= _RUN_LIMIT_PER_HOUR:
                retry_after = int(_window_seconds - (now - bucket[0])) if bucket else _window_seconds
                return Response(
                    content='{"detail":"Rate limit exceeded"}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": str(max(1, retry_after))},
                )
            bucket.append(now)
        return await call_next(request)
