"""Tenant governance run rate limit middleware."""

from __future__ import annotations

import time

from app.middleware import tenant_rate_limit as rl


def test_memory_rate_limit_blocks_after_threshold(monkeypatch):
    monkeypatch.setattr(rl, "get_redis_client", lambda: None)
    rl._buckets.clear()
    tenant = "test-tenant"
    now = time.time()
    for _ in range(rl._RUN_LIMIT_PER_HOUR):
        limited, _ = rl._memory_rate_limited(tenant, now)
        assert limited is False
    limited, retry_after = rl._memory_rate_limited(tenant, now)
    assert limited is True
    assert retry_after >= 1
