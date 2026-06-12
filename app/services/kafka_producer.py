"""Apache Kafka event publisher for webhooks, governance runs, and automation."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from aaf.config import get_settings

_log = logging.getLogger("aaf.kafka")

TOPIC_WEBHOOKS_GITHUB = "casantris.webhooks.github"
TOPIC_WEBHOOKS_JIRA = "casantris.webhooks.jira"
TOPIC_WEBHOOKS_GITLAB = "casantris.webhooks.gitlab"
TOPIC_GOVERNANCE_RUNS = "casantris.governance.runs"
TOPIC_AUTOMATION_ACTIONS = "casantris.automation.actions"
TOPIC_DLQ = "casantris.dlq"


def _event_envelope(
    *,
    event_type: str,
    payload: dict[str, Any],
    tenant_id: Optional[int] = None,
) -> dict[str, Any]:
    return {
        "event_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "type": event_type,
        "payload": payload,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }


def kafka_enabled() -> bool:
    settings = get_settings()
    return bool(settings.kafka_enabled and settings.kafka_bootstrap_servers.strip())


async def _publish_async(topic: str, message: dict[str, Any], *, key: Optional[str] = None) -> bool:
    settings = get_settings()
    try:
        from aiokafka import AIOKafkaProducer
    except ImportError:
        _log.warning("aiokafka_not_installed")
        return False

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        client_id=settings.kafka_client_id,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )
    await producer.start()
    try:
        await producer.send_and_wait(topic, message, key=key)
        return True
    finally:
        await producer.stop()


def publish_event(
    topic: str,
    *,
    event_type: str,
    payload: dict[str, Any],
    tenant_id: Optional[int] = None,
    partition_key: Optional[str] = None,
) -> bool:
    if not kafka_enabled():
        return False
    envelope = _event_envelope(event_type=event_type, payload=payload, tenant_id=tenant_id)
    try:
        return asyncio.run(_publish_async(topic, envelope, key=partition_key or envelope["event_id"]))
    except Exception:  # noqa: BLE001
        _log.exception("kafka_publish_failed", extra={"topic": topic, "type": event_type})
        publish_dlq(original_topic=topic, envelope=envelope, error="publish_failed")
        return False


def publish_dlq(*, original_topic: str, envelope: dict[str, Any], error: str) -> None:
    if not kafka_enabled():
        return
    settings = get_settings()
    dlq = {
        **envelope,
        "dlq_reason": error,
        "original_topic": original_topic,
    }
    try:
        asyncio.run(_publish_async(settings.kafka_dlq_topic or TOPIC_DLQ, dlq))
    except Exception:  # noqa: BLE001
        _log.exception("kafka_dlq_publish_failed", extra={"topic": original_topic})


def publish_webhook_event(
    source: str,
    event_type: str,
    payload: dict[str, Any],
    *,
    tenant_id: Optional[int] = None,
) -> bool:
    topic_map = {
        "github": TOPIC_WEBHOOKS_GITHUB,
        "jira": TOPIC_WEBHOOKS_JIRA,
        "gitlab": TOPIC_WEBHOOKS_GITLAB,
    }
    topic = topic_map.get(source)
    if not topic:
        return False
    return publish_event(
        topic,
        event_type=event_type,
        payload=payload,
        tenant_id=tenant_id,
        partition_key=str(payload.get("repository", {}).get("full_name") or payload.get("issue", {}).get("key") or ""),
    )


def publish_governance_run_event(
    run_id: int,
    tenant_id: Optional[int],
    *,
    status: str,
    extra: Optional[dict[str, Any]] = None,
) -> bool:
    payload = {"run_id": run_id, "status": status, **(extra or {})}
    return publish_event(
        TOPIC_GOVERNANCE_RUNS,
        event_type="governance.run.status",
        payload=payload,
        tenant_id=tenant_id,
        partition_key=str(run_id),
    )


def publish_automation_action(
    *,
    tenant_id: Optional[int],
    action_type: str,
    decision_id: Optional[int],
    run_id: Optional[int],
    payload: dict[str, Any],
) -> bool:
    body = {
        "action_type": action_type,
        "decision_id": decision_id,
        "run_id": run_id,
        **payload,
    }
    return publish_event(
        TOPIC_AUTOMATION_ACTIONS,
        event_type=f"automation.{action_type}",
        payload=body,
        tenant_id=tenant_id,
        partition_key=str(decision_id or run_id or ""),
    )
