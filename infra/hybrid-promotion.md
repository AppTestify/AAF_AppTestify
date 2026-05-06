# Hybrid Promotion Workflow (Draft)

## Environments
- **staging**: fast feedback, ephemeral test data.
- **pre-prod**: production-like controls and integration checks.
- **prod**: customer traffic with strict change windows.

## Deployment Rules
- Artifact immutability across all environments (same image digest/build id).
- Environment overlays only for config/secrets and routing.
- Promotion requires:
  - CI green
  - smoke E2E passing
  - telemetry sanity thresholds within bounds

## Rollback Guardrails
- Keep previous artifact available in each environment.
- One-command rollback path for API, worker, frontend.
- Post-rollback validation includes health, auth, and run-processing smoke checks.
