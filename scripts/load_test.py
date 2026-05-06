"""Simple load runner for Milestone-1 baseline profiling."""

from __future__ import annotations

import argparse
import statistics
import threading
import time
from typing import List

import httpx


def _worker(base_url: str, path: str, duration_s: int, out: List[float], errors: List[int]) -> None:
    end = time.time() + duration_s
    with httpx.Client(timeout=5.0) as client:
        while time.time() < end:
            start = time.time()
            try:
                resp = client.get(f"{base_url.rstrip('/')}{path}")
                if resp.status_code >= 500:
                    errors.append(resp.status_code)
            except Exception:
                errors.append(599)
            out.append((time.time() - start) * 1000)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--path", default="/health")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()

    latencies: List[float] = []
    errors: List[int] = []
    threads = [
        threading.Thread(target=_worker, args=(args.base_url, args.path, args.duration, latencies, errors), daemon=True)
        for _ in range(args.concurrency)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if not latencies:
        print("No samples collected.")
        return 1
    p95 = sorted(latencies)[int(len(latencies) * 0.95) - 1]
    p99 = sorted(latencies)[int(len(latencies) * 0.99) - 1]
    report = {
        "samples": len(latencies),
        "errors": len(errors),
        "error_rate": round(len(errors) / max(1, len(latencies)), 4),
        "mean_ms": round(statistics.mean(latencies), 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
    }
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
