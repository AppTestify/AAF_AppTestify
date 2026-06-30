# Threat Model (v2 Pre-GA Release)

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
- **Credential leakage (T-001)**: `Fernet` symmetric encryption is strictly enforced for `credentials_json` at rest, and masked provider key references are used in API responses.
- **Unauthorized actions / Session Hijacking (T-002)**: Strict `httpOnly`, `secure`, and `samesite="strict"` cookies are used for JWT auth instead of raw Bearer tokens in localStorage, protecting API routes.
- **Auth Abuse / Brute Force (T-003)**: DB-backed auth rate limiting (`AuthRateLimit` table) explicitly bounds repeated login attempts.
- **Cross-origin attacks (T-011)**: Production `CORSMiddleware` configuration blocks wildcard and localhost origins, tightly restricting cross-site integrations.
- **Undetected failures**: observability summary + Prometheus metrics + alert rule evaluation.
- **Run processing abuse**: queue depth tracking, bounded retries, dead-letter counting for terminal failures.

## Residual Risks
- Live connector coverage is partial (exceptions remain documented by connector mode).
- Formal key rotation and secrets vault integrations are not fully automated yet.
