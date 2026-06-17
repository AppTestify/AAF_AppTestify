from __future__ import annotations

import httpx

from app.services.http_resilience import classify_http_error
from app.services.integration_signals import connector_signal
from app.services.observability import record_connector_call, snapshot


class _ConnectorStub:
    connector_name = "github"
    enabled = True
    config_json = {"repo": "owner/repo"}
    encrypted_credentials_json = None


def test_connector_signal_falls_back_with_error_category(monkeypatch):
    def _boom(*args, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("app.services.integration_signals.fetch_github_signal", _boom)
    out = connector_signal(_ConnectorStub())
    assert out["mode"] == "fallback_error"
    assert out["error_category"] == "unknown"  # timeout raised outside resilience wrapper
    assert out["freshness"] == "degraded"


def test_observability_connector_window_metrics():
    record_connector_call("github", status="ok", latency_ms=120)
    record_connector_call("jira", status="error", latency_ms=210, error_category="timeout")
    snap = snapshot(window_seconds=900)
    assert snap["connector_calls_total"] >= 2
    assert "connector_error_rate" in snap
    assert "failure_recovery" in snap


def test_classify_http_error_status_and_timeout():
    timeout_kind, _, _ = classify_http_error(httpx.TimeoutException("timeout"))
    assert timeout_kind == "timeout"

    req = httpx.Request("GET", "https://example.com")
    resp = httpx.Response(429, request=req)
    http_err = httpx.HTTPStatusError("rate", request=req, response=resp)
    kind, code, _ = classify_http_error(http_err)
    assert kind == "rate_limit"
    assert code == 429
