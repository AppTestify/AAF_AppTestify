# On-Call Triage Runbook

## First 10 Minutes
- Verify alert source and severity.
- Inspect observability summary (`error_rate`, `latency_ms_p95`, `slo_burn_rate`, `failure_recovery`).
- Check connector degradation (`connector_error_rate`, `connector_error_categories`).

## Quick Isolation
- API path issue: inspect `endpoints_top` and recent spans.
- Worker issue: inspect run queue depth and retry/dead-letter counts.
- Connector issue: validate impacted connector and identify auth/rate-limit/network category.

## Mitigation Actions
- Reduce blast radius by disabling unstable connector(s) tenant-by-tenant.
- Trigger rollback if core SLO or auth controls are impacted.
- Escalate SEV-1 immediately with stakeholder notification.
