# Runbook: Apache OSS Scalability

## Enable scale profile (dev)

```bash
docker compose --profile scale up -d postgres redis api worker kafka opensearch kafka-consumer apisix
export KAFKA_ENABLED=true
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export OPENSEARCH_ENABLED=true
export OPENSEARCH_URL=http://localhost:9200
```

## Verify Kafka consumer

```bash
docker compose logs -f kafka-consumer
# Publish test webhook — should see CI cache invalidation in logs
```

## Verify OpenSearch search

```bash
curl -s 'http://localhost:9200/casantris-runs-v1/_search?q=prompt:release'
```

## APISIX smoke

```bash
APISIX_GATEWAY_URL=http://localhost:9080 ./scripts/smoke.sh
```

## Production Helm

```bash
helm upgrade --install casantris ./helm/casantris \
  --set celery.enabled=true \
  --set kafka.enabled=true \
  --set kafka.bootstrapServers=kafka:9092 \
  --set opensearch.enabled=true \
  --set opensearch.url=http://opensearch:9200 \
  --set integration.mode=camel
```

## DLQ alerts

Monitor `casantris.dlq` topic lag. Alert routing: `infra/observability-alert-routing.yaml` — add rule for `kafka_dlq_depth`.

## Optional live connector CI

Set repo variable `CONNECTOR_LIVE_CI=1` and secrets for GitHub/Jira tokens.
