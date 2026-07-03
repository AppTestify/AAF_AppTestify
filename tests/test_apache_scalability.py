"""Contract tests for Apache OSS scalability components."""

from __future__ import annotations

import pytest

from aaf.config import get_settings
from app.services.kafka_producer import (
    TOPIC_AUTOMATION_ACTIONS,
    TOPIC_DLQ,
    TOPIC_GOVERNANCE_RUNS,
    TOPIC_WEBHOOKS_GITHUB,
    _event_envelope,
    kafka_enabled,
)
from app.services.run_jobs import should_use_in_process_worker, use_celery
from app.services.search_index import opensearch_enabled


def test_event_envelope_shape():
    env = _event_envelope(event_type="github.workflow_run", payload={"repo": "o/r"}, tenant_id=1)
    assert env["type"] == "github.workflow_run"
    assert env["tenant_id"] == 1
    assert "event_id" in env
    assert "occurred_at" in env


def test_kafka_topics_defined():
    assert TOPIC_WEBHOOKS_GITHUB.startswith("casantris.")
    assert TOPIC_GOVERNANCE_RUNS == "casantris.governance.runs"
    assert TOPIC_AUTOMATION_ACTIONS == "casantris.automation.actions"
    assert TOPIC_DLQ == "casantris.dlq"


def test_kafka_disabled_by_default(monkeypatch):
    monkeypatch.delenv("KAFKA_ENABLED", raising=False)
    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)
    from app import deps

    deps.settings_dep.cache_clear()
    assert kafka_enabled() is False
    deps.settings_dep.cache_clear()


def test_in_process_worker_gated_when_celery_configured(monkeypatch):
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    from app import deps

    deps.settings_dep.cache_clear()
    assert use_celery() is True
    assert should_use_in_process_worker() is False
    deps.settings_dep.cache_clear()


def test_opensearch_disabled_by_default(monkeypatch):
    monkeypatch.delenv("OPENSEARCH_ENABLED", raising=False)
    from app import deps

    deps.settings_dep.cache_clear()
    assert opensearch_enabled() is False
    deps.settings_dep.cache_clear()


def test_camel_route_registry():
    from app.integration.camel_worker import execute_camel_route

    out = execute_camel_route("unknown_action", {}, tenant_id=None)
    assert out["status"] == "ignored"


def test_kafka_worker_topics():
    from app.consumers.kafka_worker import WEBHOOK_TOPICS
    assert "casantris.webhooks.github" in WEBHOOK_TOPICS
    assert "casantris.webhooks.jira" in WEBHOOK_TOPICS
    assert "casantris.webhooks.gitlab" in WEBHOOK_TOPICS


@pytest.mark.asyncio
async def test_kafka_worker_consume_loop(monkeypatch):
    import sys
    from unittest.mock import AsyncMock, MagicMock
    from app.consumers.kafka_worker import WEBHOOK_TOPICS

    mock_consumer = MagicMock()
    mock_consumer.start = AsyncMock()
    mock_consumer.stop = AsyncMock()

    class AsyncIterator:
        def __init__(self):
            pass

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    mock_consumer.__aiter__ = lambda s: AsyncIterator()

    mock_aiokafka = MagicMock()
    mock_aiokafka.AIOKafkaConsumer = MagicMock(return_value=mock_consumer)

    orig_aiokafka = sys.modules.get("aiokafka")
    sys.modules["aiokafka"] = mock_aiokafka

    try:
        from app.consumers.kafka_worker import _consume_loop
        await _consume_loop()

        mock_aiokafka.AIOKafkaConsumer.assert_called_once()
        args, kwargs = mock_aiokafka.AIOKafkaConsumer.call_args
        for topic in WEBHOOK_TOPICS:
            assert topic in args
        # Ensure it does NOT consume TOPIC_AUTOMATION_ACTIONS
        from app.services.kafka_producer import TOPIC_AUTOMATION_ACTIONS
        assert TOPIC_AUTOMATION_ACTIONS not in args
    finally:
        if orig_aiokafka is not None:
            sys.modules["aiokafka"] = orig_aiokafka
        else:
            sys.modules.pop("aiokafka", None)


@pytest.mark.asyncio
async def test_camel_worker_consume_loop(monkeypatch):
    import sys
    from unittest.mock import AsyncMock, MagicMock
    from app.services.kafka_producer import TOPIC_AUTOMATION_ACTIONS

    mock_consumer = MagicMock()
    mock_consumer.start = AsyncMock()
    mock_consumer.stop = AsyncMock()

    mock_msg = MagicMock()
    mock_msg.topic = TOPIC_AUTOMATION_ACTIONS
    mock_msg.value = {
        "tenant_id": 123,
        "payload": {
            "action_type": "jira_blocker",
            "run_id": 1,
            "dry_run": True
        }
    }

    class AsyncIterator:
        def __init__(self):
            self.delivered = False

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self.delivered:
                self.delivered = True
                return mock_msg
            raise StopAsyncIteration

    mock_consumer.__aiter__ = lambda s: AsyncIterator()

    mock_aiokafka = MagicMock()
    mock_aiokafka.AIOKafkaConsumer = MagicMock(return_value=mock_consumer)

    orig_aiokafka = sys.modules.get("aiokafka")
    sys.modules["aiokafka"] = mock_aiokafka

    try:
        mock_execute = MagicMock(return_value={"status": "success"})
        monkeypatch.setattr("app.integration.camel_worker.execute_camel_route", mock_execute)

        from app.integration.camel_worker import _consume_loop
        await _consume_loop()

        mock_aiokafka.AIOKafkaConsumer.assert_called_once()
        args, kwargs = mock_aiokafka.AIOKafkaConsumer.call_args
        assert TOPIC_AUTOMATION_ACTIONS in args

        mock_execute.assert_called_once_with(
            "jira_blocker",
            {"action_type": "jira_blocker", "run_id": 1, "dry_run": True},
            tenant_id=123
        )
    finally:
        if orig_aiokafka is not None:
            sys.modules["aiokafka"] = orig_aiokafka
        else:
            sys.modules.pop("aiokafka", None)


@pytest.mark.parametrize(
    "settings_patch,expected",
    [
        ({"kafka_enabled": True, "kafka_bootstrap_servers": "kafka:9092"}, True),
        ({"kafka_enabled": False, "kafka_bootstrap_servers": "kafka:9092"}, False),
    ],
)
def test_kafka_enabled_config(monkeypatch, settings_patch, expected):
    for k, v in settings_patch.items():
        monkeypatch.setenv(k.upper(), str(v).lower() if isinstance(v, bool) else str(v))
    from app import deps

    deps.settings_dep.cache_clear()
    s = get_settings()
    assert bool(s.kafka_enabled and s.kafka_bootstrap_servers.strip()) == expected
    deps.settings_dep.cache_clear()
