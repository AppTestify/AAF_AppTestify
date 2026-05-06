# Control Mapping (Draft v1)

| Control Area | Implementation Reference | Evidence Artifact |
| --- | --- | --- |
| Authentication | `app/routers/auth.py`, JWT config | Auth API tests, login audit events |
| Authorization / RBAC | `app/deps.py`, `app/routers/rbac.py` | Permission tests and role-bound endpoints |
| Tenant Isolation | tenant-scoped query patterns in routers | Cross-tenant negative tests |
| Secrets Handling | encrypted credentials in config models/services | Masked secrets in API responses |
| Auditability | `AuditEvent`, `ConfigAuditLog` models | `/reports/audit-events` exports |
| Operational Monitoring | telemetry + observability routers | Prometheus metrics snapshots |
| Failure Recovery | worker retries + dead-letter counting | run failure logs + failure metrics |

## Notes
- This mapping is a v1 external review draft and should be linked to change-management records in milestone-2.
