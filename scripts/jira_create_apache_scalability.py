#!/usr/bin/env python3
"""Create Jira epic + stories for Apache OSS Scalability Platform (T-192–T-211)."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOUD_BASE = "https://api.atlassian.com/ex/jira/a5ff7216-8c30-4859-812f-fec70776da1f"

# Set after first epic creation, or use existing key (CAS-215 may be E2E — use new epic for Apache OSS)
EPIC_KEY = "CAS-222"
EPIC_SUMMARY = "Apache OSS Scalability Platform"
EPIC_BODY = """Horizontally scale Casantris with Apache Kafka, OpenSearch, APISIX, and Camel.

**Components:** Kafka event bus · OpenSearch search · APISIX edge gateway · Camel integration worker · Celery Helm workers

**Stories:** T-192–T-211

**Design:** docs/design/apache-scalability-platform.md"""

STORIES: list[dict] = [
    {"task": "T-192", "summary": "Celery worker + beat Helm Deployments", "labels": ["apache-oss", "helm", "sprint-S0"], "body": "worker-deployment.yaml, beat-deployment.yaml; env mirrors API."},
    {"task": "T-193", "summary": "CD deploys worker/beat; gate in-process thread worker", "labels": ["apache-oss", "celery", "sprint-S0"], "body": "app/main.py gates start_worker(); run_jobs real queue depth."},
    {"task": "T-194", "summary": "K8s Service + Ingress templates for API", "labels": ["apache-oss", "helm", "sprint-S0"], "body": "service.yaml, ingress.yaml in casantris chart."},
    {"task": "T-195", "summary": "Kafka in compose + Helm values", "labels": ["apache-oss", "kafka", "sprint-S1"], "body": "docker-compose --profile scale; helm kafka consumer deployment."},
    {"task": "T-196", "summary": "kafka_producer.py + config", "labels": ["apache-oss", "kafka", "sprint-S1"], "body": "KAFKA_BOOTSTRAP_SERVERS in aaf/config.py; idempotent event envelope."},
    {"task": "T-197", "summary": "Webhook ingress → Kafka topics", "labels": ["apache-oss", "kafka", "sprint-S1"], "body": "casantris.webhooks.* topics; async accept when kafka_enabled."},
    {"task": "T-198", "summary": "Kafka consumers + DLQ topic", "labels": ["apache-oss", "kafka", "sprint-S1"], "body": "app/consumers/kafka_worker.py; casantris.dlq; alert routing."},
    {"task": "T-199", "summary": "OpenSearch in compose + Helm values", "labels": ["apache-oss", "opensearch", "sprint-S2"], "body": "Single-node dev; values.opensearch for prod URL."},
    {"task": "T-200", "summary": "search_index.py", "labels": ["apache-oss", "opensearch", "sprint-S2"], "body": "Index runs, cases, audit-events with tenant_id."},
    {"task": "T-201", "summary": "Index on run complete", "labels": ["apache-oss", "opensearch", "sprint-S2"], "body": "Hook in run_jobs.py post-commit."},
    {"task": "T-202", "summary": "Search API backend switch", "labels": ["apache-oss", "opensearch", "sprint-S2"], "body": "search.py OpenSearch when OPENSEARCH_URL set; ILIKE fallback."},
    {"task": "T-203", "summary": "APISIX config + compose profile", "labels": ["apache-oss", "apisix", "sprint-S3"], "body": "infra/apisix/ routes /api/* → API upstream."},
    {"task": "T-204", "summary": "APISIX plugins: rate-limit, prometheus, cors", "labels": ["apache-oss", "apisix", "sprint-S3"], "body": "limit-req, prometheus, cors in apisix.yaml."},
    {"task": "T-205", "summary": "CD smoke through APISIX URL", "labels": ["apache-oss", "apisix", "sprint-S3"], "body": "scripts/smoke.sh APISIX_GATEWAY_URL support."},
    {"task": "T-206", "summary": "Camel integration worker bridge", "labels": ["apache-oss", "camel", "sprint-S4"], "body": "app/integration/camel_worker.py consuming automation topic."},
    {"task": "T-207", "summary": "jira_blocker.camel.yaml route", "labels": ["apache-oss", "camel", "sprint-S4"], "body": "integrations/camel/jira_blocker.camel.yaml."},
    {"task": "T-208", "summary": "hold_release.camel.yaml route", "labels": ["apache-oss", "camel", "sprint-S4"], "body": "integrations/camel/hold_release.camel.yaml."},
    {"task": "T-209", "summary": "integration_mode=camel publishes to Kafka", "labels": ["apache-oss", "camel", "sprint-S4"], "body": "action_automation.py feature flag behind integration_mode."},
    {"task": "T-210", "summary": "Design doc + runbook", "labels": ["apache-oss", "docs", "sprint-S5"], "body": "docs/design/apache-scalability-platform.md + runbook."},
    {"task": "T-211", "summary": "Integration tests", "labels": ["apache-oss", "tests", "sprint-S5"], "body": "tests/test_apache_scalability.py contract tests."},
]


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def request(method: str, url: str, auth: str, payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            body = json.loads(raw) if raw else {"error": str(exc)}
        except json.JSONDecodeError:
            body = {"error": raw or str(exc)}
        return exc.code, body


def create_epic(auth: str) -> str:
    payload = {
        "fields": {
            "project": {"key": "CAS"},
            "issuetype": {"name": "Epic"},
            "summary": EPIC_SUMMARY,
            "description": EPIC_BODY,
            "labels": ["apache-oss", "scalability", "infrastructure"],
        }
    }
    status, result = request("POST", f"{CLOUD_BASE}/rest/api/3/issue", auth, payload)
    if status not in (200, 201):
        raise RuntimeError(f"Failed epic: {status} {result}")
    return result["key"]


def create_story(auth: str, epic_key: str, *, task: str, summary: str, body: str, labels: list[str]) -> str:
    payload = {
        "fields": {
            "project": {"key": "CAS"},
            "issuetype": {"name": "Story"},
            "summary": f"{task}: {summary}",
            "description": body,
            "parent": {"key": epic_key},
            "labels": labels,
        }
    }
    status, result = request("POST", f"{CLOUD_BASE}/rest/api/3/issue", auth, payload)
    if status not in (200, 201):
        raise RuntimeError(f"Failed {task}: {status} {result}")
    return result["key"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stories-only", action="store_true")
    args = parser.parse_args()

    env = {**load_env(ROOT / ".env"), **os.environ}
    email = env.get("JIRA_EMAIL", "").strip()
    token = env.get("JIRA_API_TOKEN", "").strip()
    if not email or not token:
        print("Set JIRA_EMAIL and JIRA_API_TOKEN in .env", file=sys.stderr)
        return 1

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    epic_key = EPIC_KEY
    if not args.stories_only:
        epic_key = create_epic(auth)
        print(f"Created epic {epic_key}: {EPIC_SUMMARY}")
        print(f'Update EPIC_KEY = "{epic_key}" in scripts/jira_create_apache_scalability.py')
    elif not epic_key:
        print("Set EPIC_KEY or omit --stories-only", file=sys.stderr)
        return 1
    else:
        print(f"Using epic {epic_key}")

    created: list[str] = []
    for story in STORIES:
        key = create_story(auth, epic_key, **story)
        created.append(key)
        print(f"Created {key}: {story['task']} {story['summary']}")

    print(f"\nDone — epic {epic_key} + {len(created)} stories")
    print("Story keys:", ", ".join(created))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
