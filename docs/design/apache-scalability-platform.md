# Apache OSS Scalability Platform

Casantris scales horizontally with four Apache Foundation components plus Celery Helm workers.

## Architecture

| Layer | Component | Purpose |
|-------|-----------|---------|
| Edge | Apache APISIX | Rate limiting, CORS, Prometheus, route `/api/*` → API |
| Events | Apache Kafka | Webhooks, governance runs, automation actions, DLQ |
| Search | Apache OpenSearch | Sub-200ms global search at 100k+ runs |
| Integrations | Apache Camel | Jira blocker + hold-release routes from Kafka |
| Workers | Celery + Kafka consumer | Governance runs, digests, async webhook processing |

## Kafka topic catalog

| Topic | Producer | Consumer |
|-------|----------|----------|
| `casantris.webhooks.github` | API webhooks | kafka_worker → CI cache invalidation |
| `casantris.webhooks.jira` | API webhooks | kafka_worker |
| `casantris.webhooks.gitlab` | API webhooks | kafka_worker |
| `casantris.governance.runs` | run_jobs on complete | analytics (future) |
| `casantris.automation.actions` | action_automation (camel mode) | camel_worker |
| `casantris.dlq` | failed publishes/handlers | ops alert |

Event envelope:

```json
{
  "event_id": "uuid",
  "tenant_id": 1,
  "type": "github.workflow_run",
  "payload": {},
  "occurred_at": "ISO8601"
}
```

## OpenSearch indices

- `casantris-runs-v1` — prompt, status, recommended_action, tenant_id
- `casantris-cases-v1` — title, status, latest_run_id
- `casantris-audit-events-v1` — area, action, summary

## APISIX route map

- `/api/*` → `casantris-api:8000` (limit-req 120/s, prometheus, cors)
- `/health` → API health probe

## Configuration

```bash
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
OPENSEARCH_ENABLED=true
OPENSEARCH_URL=http://opensearch:9200
INTEGRATION_MODE=camel   # python | camel
APISIX_GATEWAY_URL=http://apisix:9080
```

## Local dev

```bash
docker compose --profile scale up -d
```

Adds Kafka, OpenSearch, APISIX, and kafka-consumer services.

## Related

- [CAS-202 Actionable Automation](https://apptestify.atlassian.net/browse/CAS-202)
- Runbook: `docs/runbooks/apache-scalability.md`
