# Release and Rollback Runbook

## Promotion Path
- `staging` -> `pre-prod` -> `prod`
- Promote only when CI is green and smoke tests pass.

## Release Checklist
1. Confirm latest `main` build has passing backend/frontend jobs.
2. Apply migrations in target environment.
3. Deploy API and worker components.
4. Deploy frontend static bundle.
5. Validate `/health`, authenticated `/api/v1/telemetry/summary`, and a smoke governance run.

## Rollback Strategy
1. Roll back to last known-good container/image tag.
2. If migration introduced issue, execute pre-approved DB rollback script.
3. Re-run smoke tests and confirm queue/process stability.
4. Broadcast incident status and open follow-up RCA.
