# Load Baseline Report (Milestone-1)

## Scenarios
- Health endpoint sustained load (`/health`)
- Observability endpoint read pressure (`/api/v1/telemetry/observability/summary`)
- Governance run creation burst (`/api/v1/governance/runs`)

## Runner
- Script: `python scripts/load_test.py --base-url http://localhost:8000 --path /health --duration 60 --concurrency 20`

## Metrics to Capture
- p95 / p99 response latency
- request error rate
- queue depth and retry growth under stress
- connector error-rate changes during run bursts

## Initial Tuning Actions
- Increase API worker count in staging.
- Separate governance run worker from API process under high load.
- Reduce heavy telemetry polling intervals in UI dashboards.
