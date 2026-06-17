"""Pub/sub mechanism for real-time governance run events."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, AsyncIterator

from aaf.config import get_settings

_log = logging.getLogger(__name__)

# Fallback in-memory bus for single-process (no-redis) deployments
# Maps run_id -> list of asyncio.Queue
_mem_queues: dict[int, list[asyncio.Queue]] = defaultdict(list)


def publish_run_event_sync(run_id: int, event_name: str, data: dict[str, Any] | None = None) -> None:
    """Publish an event from the synchronous worker thread/process."""
    payload = json.dumps({"event": event_name, "data": data or {}})
    settings = get_settings()
    url = settings.redis_url or settings.celery_broker_url
    if url:
        try:
            import redis
            client = redis.Redis.from_url(url)
            client.publish(f"governance_run:{run_id}", payload)
            client.close()
        except Exception as e:
            _log.warning(f"Failed to publish run event to redis: {e}")
    else:
        # Fallback to in-memory queue.
        # This is called from a sync thread, so we put into asyncio queue safely using call_soon_threadsafe.
        for q in _mem_queues.get(run_id, []):
            try:
                q.get_loop().call_soon_threadsafe(q.put_nowait, payload)
            except Exception:
                pass


async def subscribe_run_events(run_id: int) -> AsyncIterator[str]:
    """Yield SSE formatted strings for a given run_id."""
    settings = get_settings()
    url = settings.redis_url or settings.celery_broker_url
    if url:
        import redis.asyncio as aioredis
        client = aioredis.from_url(url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(f"governance_run:{run_id}")
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    try:
                        data = json.loads(message["data"])
                        event_name = data.get("event", "message")
                        event_data = data.get("data", {})
                        yield f"event: {event_name}\ndata: {json.dumps(event_data)}\n\n"
                        if event_name in ("result_ready", "error"):
                            break
                    except Exception:
                        pass
                else:
                    yield ": keepalive\n\n"
                    await asyncio.sleep(0.5)
        finally:
            await pubsub.unsubscribe(f"governance_run:{run_id}")
            await client.close()
    else:
        q: asyncio.Queue[str] = asyncio.Queue()
        _mem_queues[run_id].append(q)
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=1.0)
                    data = json.loads(payload)
                    event_name = data.get("event", "message")
                    event_data = data.get("data", {})
                    yield f"event: {event_name}\ndata: {json.dumps(event_data)}\n\n"
                    if event_name in ("result_ready", "error"):
                        break
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            if q in _mem_queues[run_id]:
                _mem_queues[run_id].remove(q)
            if not _mem_queues[run_id]:
                del _mem_queues[run_id]
