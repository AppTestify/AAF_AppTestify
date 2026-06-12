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
