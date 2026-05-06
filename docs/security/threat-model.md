# Threat Model (Draft v1)

## Scope
- API authentication/authorization flows
- Tenant isolation boundaries
- Connector and AI provider credential handling
- Audit trail integrity and retention

## Primary Assets
- Tenant data and governance outputs
- Encrypted connector/provider credentials
- JWT signing secret and runtime environment secrets
- Audit evidence for release decisions

## Threats and Controls
- **Broken tenant isolation**: tenant-scoped queries in API routers; superadmin-only cross-tenant access checks.
- **Credential leakage**: encrypted-at-rest `credentials_json` usage and masked provider key references in responses.
- **Unauthorized actions**: RBAC permission checks and JWT auth for protected API routes.
- **Undetected failures**: observability summary + Prometheus metrics + alert rule evaluation.
- **Run processing abuse**: queue depth tracking, bounded retries, dead-letter counting for terminal failures.

## Residual Risks
- Live connector coverage is partial (exceptions remain documented by connector mode).
- Formal key rotation and secrets vault integrations are not fully automated yet.
