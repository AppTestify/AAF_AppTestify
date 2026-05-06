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


_lock = Lock()
_started_at = time.time()
_requests: "deque[RequestEvent]" = deque(maxlen=5000)
_runs: "deque[RunEvent]" = deque(maxlen=2000)
_inflight_requests = 0
_run_queue_depth = 0


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


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = int((len(values) - 1) * pct)
    return values[idx]


def snapshot(window_seconds: int = 300) -> dict:
    now = time.time()
    with _lock:
        req_window = [r for r in _requests if now - r.ts <= window_seconds]
        run_window = [r for r in _runs if now - r.ts <= window_seconds]
        inflight = _inflight_requests
        queue_depth = _run_queue_depth

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

    uptime = int(now - _started_at)
    return {
        "window_seconds": window_seconds,
        "uptime_seconds": uptime,
        "requests_total": total,
        "requests_per_min": round((total / max(window_seconds, 1)) * 60, 2),
        "error_rate": round((errors / total), 4) if total else 0.0,
        "latency_ms_p50": round(_percentile(latencies, 0.50), 2),
        "latency_ms_p95": round(_percentile(latencies, 0.95), 2),
        "latency_ms_p99": round(_percentile(latencies, 0.99), 2),
        "inflight_requests": inflight,
        "run_queue_depth": queue_depth,
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
    ]
    return "\n".join(lines) + "\n"
