"""In-process observability metrics for API and worker health."""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from threading import Lock
import time
from typing import Optional


@dataclass
class RequestEvent:
    ts: float
    method: str
    path: str
    status_code: int
    elapsed_ms: float


@dataclass
class RunEvent:
    ts: float
    status: str
    elapsed_ms: float
    retry_count: int


@dataclass
class SpanEvent:
    ts: float
    name: str
    duration_ms: float
    status: str
    attributes: dict


@dataclass
class ConnectorEvent:
    ts: float
    connector: str
    status: str
    latency_ms: float
    error_category: Optional[str]


_lock = Lock()
_started_at = time.time()
_requests: "deque[RequestEvent]" = deque(maxlen=5000)
_runs: "deque[RunEvent]" = deque(maxlen=2000)
_spans: "deque[SpanEvent]" = deque(maxlen=4000)
_connectors: "deque[ConnectorEvent]" = deque(maxlen=4000)
_inflight_requests = 0
_run_queue_depth = 0
_dead_letter_count = 0


def set_run_queue_depth(depth: int) -> None:
    global _run_queue_depth
    with _lock:
        _run_queue_depth = max(0, depth)


def record_request(method: str, path: str, status_code: int, elapsed_ms: float) -> None:
    global _inflight_requests
    with _lock:
        _requests.append(
            RequestEvent(
                ts=time.time(),
                method=method,
                path=path,
                status_code=status_code,
                elapsed_ms=elapsed_ms,
            )
        )
        _inflight_requests = max(0, _inflight_requests - 1)


def request_started() -> None:
    global _inflight_requests
    with _lock:
        _inflight_requests += 1


def record_run(status: str, elapsed_ms: float, retry_count: int) -> None:
    with _lock:
        _runs.append(RunEvent(ts=time.time(), status=status, elapsed_ms=elapsed_ms, retry_count=retry_count))


def record_span(name: str, duration_ms: float, status: str, attributes: Optional[dict] = None) -> None:
    with _lock:
        _spans.append(
            SpanEvent(
                ts=time.time(),
                name=name,
                duration_ms=duration_ms,
                status=status,
                attributes=attributes or {},
            )
        )


def record_connector_call(
    connector: str,
    *,
    status: str,
    latency_ms: float,
    error_category: Optional[str] = None,
) -> None:
    with _lock:
        _connectors.append(
            ConnectorEvent(
                ts=time.time(),
                connector=connector,
                status=status,
                latency_ms=latency_ms,
                error_category=error_category,
            )
        )


def record_dead_letter() -> None:
    global _dead_letter_count
    with _lock:
        _dead_letter_count += 1


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = int((len(values) - 1) * pct)
    return values[idx]


def _window_metrics(req_window: list[RequestEvent], run_window: list[RunEvent], window_seconds: int) -> dict:
    total = len(req_window)
    errors = sum(1 for r in req_window if r.status_code >= 500)
    latencies = [r.elapsed_ms for r in req_window]
    by_endpoint = Counter(f"{r.method} {r.path}" for r in req_window)
    endpoint_errors = Counter(f"{r.method} {r.path}" for r in req_window if r.status_code >= 500)

    runs_total = len(run_window)
    run_failed = sum(1 for r in run_window if r.status == "failed")
    run_succeeded = sum(1 for r in run_window if r.status == "succeeded")
    run_retried = sum(1 for r in run_window if r.retry_count > 0)
    run_latencies = [r.elapsed_ms for r in run_window]

    return {
        "window_seconds": window_seconds,
        "requests_total": total,
        "requests_per_min": round((total / max(window_seconds, 1)) * 60, 2),
        "error_rate": round((errors / total), 4) if total else 0.0,
        "latency_ms_p50": round(_percentile(latencies, 0.50), 2),
        "latency_ms_p95": round(_percentile(latencies, 0.95), 2),
        "latency_ms_p99": round(_percentile(latencies, 0.99), 2),
        "runs_total": runs_total,
        "runs_succeeded": run_succeeded,
        "runs_failed": run_failed,
        "runs_retried": run_retried,
        "run_latency_ms_p95": round(_percentile(run_latencies, 0.95), 2),
        "endpoints_top": [
            {
                "endpoint": endpoint,
                "count": count,
                "errors": endpoint_errors.get(endpoint, 0),
            }
            for endpoint, count in by_endpoint.most_common(12)
        ],
    }


def _connector_metrics(conn_window: list[ConnectorEvent]) -> dict:
    if not conn_window:
        return {
            "connector_calls_total": 0,
            "connector_error_rate": 0.0,
            "connector_latency_ms_p95": 0.0,
            "connector_status_counts": {},
            "connector_error_categories": {},
        }
    total = len(conn_window)
    failed = sum(1 for c in conn_window if c.status != "ok")
    latencies = [c.latency_ms for c in conn_window]
    status_counts = Counter(c.status for c in conn_window)
    error_categories = Counter(c.error_category for c in conn_window if c.error_category)
    return {
        "connector_calls_total": total,
        "connector_error_rate": round(failed / total, 4),
        "connector_latency_ms_p95": round(_percentile(latencies, 0.95), 2),
        "connector_status_counts": dict(status_counts),
        "connector_error_categories": dict(error_categories),
    }


def _compute_slo_burn(short_error_rate: float, long_error_rate: float, target: float = 0.999) -> dict:
    error_budget = max(1e-9, 1.0 - target)
    short_burn = round(short_error_rate / error_budget, 3)
    long_burn = round(long_error_rate / error_budget, 3)
    if short_burn > 14 and long_burn > 6:
        state = "critical"
    elif short_burn > 7 or long_burn > 3:
        state = "warning"
    else:
        state = "healthy"
    return {
        "target": target,
        "error_budget": round(error_budget, 6),
        "short_burn_rate": short_burn,
        "long_burn_rate": long_burn,
        "state": state,
    }


def _evaluate_alert_rules(metrics: dict, slo_burn: dict) -> list[dict]:
    rules = [
        {
            "id": "high_error_rate",
            "name": "High error rate",
            "triggered": metrics["error_rate"] >= 0.03,
            "severity": "critical" if metrics["error_rate"] >= 0.06 else "warning",
            "threshold": 0.03,
            "current_value": metrics["error_rate"],
        },
        {
            "id": "latency_p95_degraded",
            "name": "Latency p95 degraded",
            "triggered": metrics["latency_ms_p95"] >= 800,
            "severity": "warning",
            "threshold": 800,
            "current_value": metrics["latency_ms_p95"],
        },
        {
            "id": "run_queue_backlog",
            "name": "Run queue backlog",
            "triggered": metrics["run_queue_depth"] >= 25,
            "severity": "warning",
            "threshold": 25,
            "current_value": metrics["run_queue_depth"],
        },
        {
            "id": "slo_burn_rate",
            "name": "SLO burn rate elevated",
            "triggered": slo_burn["state"] in {"warning", "critical"},
            "severity": slo_burn["state"],
            "threshold": 3,
            "current_value": slo_burn["long_burn_rate"],
        },
    ]
    return rules


def snapshot(window_seconds: int = 300) -> dict:
    now = time.time()
    with _lock:
        req_window = [r for r in _requests if now - r.ts <= window_seconds]
        run_window = [r for r in _runs if now - r.ts <= window_seconds]
        long_window_seconds = min(3600, max(window_seconds * 12, 900))
        req_window_long = [r for r in _requests if now - r.ts <= long_window_seconds]
        inflight = _inflight_requests
        queue_depth = _run_queue_depth
        spans_recent = [s for s in _spans if now - s.ts <= long_window_seconds][-20:]
        conn_window = [c for c in _connectors if now - c.ts <= window_seconds]
        dead_letters = _dead_letter_count

    base = _window_metrics(req_window, run_window, window_seconds)
    conn_base = _connector_metrics(conn_window)
    long_base = _window_metrics(req_window_long, [], long_window_seconds)
    slo_burn = _compute_slo_burn(base["error_rate"], long_base["error_rate"])
    uptime = int(now - _started_at)
    merged = {
        **base,
        "uptime_seconds": uptime,
        "inflight_requests": inflight,
        "run_queue_depth": queue_depth,
        "slo_burn_rate": {
            "short_window_seconds": window_seconds,
            "long_window_seconds": long_window_seconds,
            "short_error_rate": base["error_rate"],
            "long_error_rate": long_base["error_rate"],
            **slo_burn,
        },
        "alert_rules": _evaluate_alert_rules(
            {"error_rate": base["error_rate"], "latency_ms_p95": base["latency_ms_p95"], "run_queue_depth": queue_depth},
            slo_burn,
        ),
        "spans_recent": [
            {
                "name": s.name,
                "duration_ms": round(float(s.duration_ms), 2),
                "status": s.status,
                "attributes": s.attributes,
                "ts": s.ts,
            }
            for s in spans_recent
        ],
        "failure_recovery": {
            "dead_letter_count": dead_letters,
            "run_retry_events": base["runs_retried"],
        },
        **conn_base,
    }
    return merged


def render_prometheus(window_seconds: int = 300) -> str:
    s = snapshot(window_seconds=window_seconds)
    lines = [
        "# HELP aaf_requests_window_total Requests in rolling window",
        "# TYPE aaf_requests_window_total gauge",
        f"aaf_requests_window_total {s['requests_total']}",
        "# HELP aaf_request_error_rate Rolling request error rate",
        "# TYPE aaf_request_error_rate gauge",
        f"aaf_request_error_rate {s['error_rate']}",
        "# HELP aaf_request_latency_p95_ms Rolling p95 request latency in ms",
        "# TYPE aaf_request_latency_p95_ms gauge",
        f"aaf_request_latency_p95_ms {s['latency_ms_p95']}",
        "# HELP aaf_inflight_requests Current in-flight requests",
        "# TYPE aaf_inflight_requests gauge",
        f"aaf_inflight_requests {s['inflight_requests']}",
        "# HELP aaf_worker_run_queue_depth Current run queue depth",
        "# TYPE aaf_worker_run_queue_depth gauge",
        f"aaf_worker_run_queue_depth {s['run_queue_depth']}",
        "# HELP aaf_worker_runs_window_total Runs in rolling window",
        "# TYPE aaf_worker_runs_window_total gauge",
        f"aaf_worker_runs_window_total {s['runs_total']}",
        "# HELP aaf_worker_run_failures_window_total Failed runs in rolling window",
        "# TYPE aaf_worker_run_failures_window_total gauge",
        f"aaf_worker_run_failures_window_total {s['runs_failed']}",
        "# HELP aaf_worker_run_latency_p95_ms Rolling p95 run latency in ms",
        "# TYPE aaf_worker_run_latency_p95_ms gauge",
        f"aaf_worker_run_latency_p95_ms {s['run_latency_ms_p95']}",
        "# HELP aaf_uptime_seconds Process uptime in seconds",
        "# TYPE aaf_uptime_seconds counter",
        f"aaf_uptime_seconds {s['uptime_seconds']}",
        "# HELP aaf_slo_burn_rate_short Current short-window SLO burn rate",
        "# TYPE aaf_slo_burn_rate_short gauge",
        f"aaf_slo_burn_rate_short {s['slo_burn_rate']['short_burn_rate']}",
        "# HELP aaf_slo_burn_rate_long Current long-window SLO burn rate",
        "# TYPE aaf_slo_burn_rate_long gauge",
        f"aaf_slo_burn_rate_long {s['slo_burn_rate']['long_burn_rate']}",
        "# HELP aaf_alert_rules_triggered Number of triggered alert rules",
        "# TYPE aaf_alert_rules_triggered gauge",
        f"aaf_alert_rules_triggered {sum(1 for r in s['alert_rules'] if r.get('triggered'))}",
        "# HELP aaf_connector_calls_total Connector calls in rolling window",
        "# TYPE aaf_connector_calls_total gauge",
        f"aaf_connector_calls_total {s.get('connector_calls_total', 0)}",
        "# HELP aaf_connector_error_rate Connector error rate in rolling window",
        "# TYPE aaf_connector_error_rate gauge",
        f"aaf_connector_error_rate {s.get('connector_error_rate', 0.0)}",
        "# HELP aaf_dead_letter_count Dead-lettered runs count",
        "# TYPE aaf_dead_letter_count counter",
        f"aaf_dead_letter_count {s.get('failure_recovery', {}).get('dead_letter_count', 0)}",
    ]
    return "\n".join(lines) + "\n"
