# Incident Response Outline (Draft v1)

## Severity Levels
- **SEV-1**: platform outage, cross-tenant leakage, auth bypass.
- **SEV-2**: degraded governance execution, repeated failed runs, elevated SLO burn.
- **SEV-3**: partial connector degradation, isolated feature regressions.

## Response Flow
1. Detect via telemetry alert rules, SLO burn state, or customer report.
2. Triage with on-call owner and identify blast radius (tenant, route, connector).
3. Mitigate using rollback/runbook action and temporary guardrails.
4. Recover by validating health endpoints, run queue, and critical workflows.
5. Document incident timeline, root cause, and follow-up actions.

## Evidence to Capture
- Request IDs and relevant logs
- Telemetry snapshots and triggered rule details
- Affected run IDs / case IDs / tenant scope
- Timeline of mitigation and validation checks
