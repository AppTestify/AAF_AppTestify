"""Kafka consumer worker — processes webhooks, CI cache invalidation, and automation actions."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from aaf.config import get_settings
from app.services.kafka_producer import (
    TOPIC_AUTOMATION_ACTIONS,
    TOPIC_DLQ,
    TOPIC_WEBHOOKS_GITHUB,
    TOPIC_WEBHOOKS_GITLAB,
    TOPIC_WEBHOOKS_JIRA,
    kafka_enabled,
    publish_dlq,
)

_log = logging.getLogger("aaf.kafka.consumer")

WEBHOOK_TOPICS = [TOPIC_WEBHOOKS_GITHUB, TOPIC_WEBHOOKS_JIRA, TOPIC_WEBHOOKS_GITLAB]


def _handle_webhook(envelope: dict[str, Any]) -> None:
    from app.routers.webhooks import invalidate_ci_cache

    payload = envelope.get("payload") or {}
    event_type = str(envelope.get("type") or "")
    if "github" in event_type or "workflow_run" in event_type:
        repo = (payload.get("repository") or {}).get("full_name", "")
        if repo:
            invalidate_ci_cache(repo)
    elif "jira" in event_type:
        issue = payload.get("issue") or {}
        key = issue.get("key", "")
        if key:
            invalidate_ci_cache(f"jira:{key}")
    elif "gitlab" in event_type:
        project = (payload.get("project") or {}).get("path_with_namespace", "")
        if project:
            invalidate_ci_cache(f"gitlab:{project}")


def _handle_automation(envelope: dict[str, Any]) -> None:
    from app.integration.camel_worker import execute_camel_route

    payload = envelope.get("payload") or {}
    action_type = str(payload.get("action_type") or "")
    if not action_type:
        return
    execute_camel_route(action_type, payload, tenant_id=envelope.get("tenant_id"))


async def _consume_loop() -> None:
    from aiokafka import AIOKafkaConsumer

    settings = get_settings()
    topics = WEBHOOK_TOPICS + [TOPIC_AUTOMATION_ACTIONS]
    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="casantris-consumers",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
    )
    await consumer.start()
    _log.info("kafka_consumer_started", extra={"topics": topics})
    try:
        async for msg in consumer:
            envelope = msg.value if isinstance(msg.value, dict) else {}
            try:
                if msg.topic in WEBHOOK_TOPICS:
                    _handle_webhook(envelope)
                elif msg.topic == TOPIC_AUTOMATION_ACTIONS:
                    _handle_automation(envelope)
            except Exception as exc:  # noqa: BLE001
                _log.exception("kafka_message_handler_failed", extra={"topic": msg.topic})
                publish_dlq(original_topic=msg.topic, envelope=envelope, error=str(exc))
    finally:
        await consumer.stop()


def main() -> None:
    if not kafka_enabled():
        _log.error("kafka_not_enabled")
        raise SystemExit(1)
    asyncio.run(_consume_loop())


if __name__ == "__main__":
    main()
