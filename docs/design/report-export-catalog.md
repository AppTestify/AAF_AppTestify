# Report Export Catalog

Epic: CAS-163 — Report exports (Excel/PDF) and platform notification configuration.

This document catalogs governance report export endpoints, file formats, and column schemas.

## Endpoints

| Report | Path | Formats | Permission |
|--------|------|---------|------------|
| Run summary | `GET /api/v1/reports/runs/summary` | `json`, `csv`, `xlsx`, `pdf` | `runs.create` |
| Audit events | `GET /api/v1/reports/audit-events` | `json`, `csv`, `xlsx`, `pdf` | `cases.manage` |
| Portfolio executive | `GET /api/v1/reports/portfolio/executive` | `json`, `xlsx`, `pdf` | `cases.manage` |
| Single run (existing) | `GET /api/v1/reports/runs/{run_id}/export` | `json`, `csv` | `runs.create` |
| Decision framing PDF (existing) | `GET /api/v1/reports/pdf/{run_id}` | `pdf` | authenticated |

Query parameters for run summary: `status`, `portfolio_project_id`, `limit` (1–5000).

Query parameters for audit events: `area`, `limit` (1–10000).

All exports are tenant-scoped unless the caller is a platform superadmin.

## Run summary columns

| Column | Type | Description |
|--------|------|-------------|
| `run_id` | int | Governance run primary key |
| `tenant_id` | int | Owning tenant |
| `portfolio_project_id` | int \| null | Linked portfolio project |
| `status` | string | Run lifecycle status |
| `prompt_id` | string \| null | Prompt library id |
| `prompt` | string | User prompt text |
| `orchestration_consensus_score` | float \| null | Orchestration consensus |
| `findings_consensus_score` | float \| null | Findings synthesis consensus |
| `findings_conflict_detected` | bool \| null | Findings conflict flag |
| `recommended_action` | string \| null | Primary recommended action |
| `utility_score` | float \| null | Utility score |
| `xi_score` | float \| null | Explainability index |
| `rar_triggered` | bool \| null | RAR loop triggered |
| `rar_loops` | int \| null | RAR iteration count |
| `primary_recommendation_source` | string \| null | Decision framing source |
| `created_at` | ISO datetime | Run start |
| `finished_at` | ISO datetime \| null | Run completion |

## Audit event columns

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Audit event id |
| `tenant_id` | int | Owning tenant |
| `actor_user_id` | int \| null | Acting user |
| `area` | string | Audit area (e.g. `governance_run`) |
| `action` | string | Action verb |
| `entity_type` | string \| null | Entity type |
| `entity_id` | string \| null | Entity identifier |
| `severity` | string | Severity band |
| `summary` | string | Human-readable summary |
| `created_at` | ISO datetime | Event timestamp |
| `before_json` | object \| null | State before change |
| `after_json` | object \| null | State after change |

## Portfolio executive sections

JSON responses mirror `ExecutivePortfolioReport`:

- Aggregate KPIs: projects, releases, confidence, consensus, high-risk counts
- `project_breakdown`: per-project release posture

Excel exports use two sheets: **Summary** (KPI rows) and **Projects** (breakdown table).

PDF exports render a one-page executive summary with KPI block and top project rows.

## File naming

| Format | Content-Disposition filename |
|--------|---------------------------|
| CSV | `governance_run_summary.csv`, `audit_events.csv` |
| XLSX | `governance_run_summary.xlsx`, `audit_events.xlsx`, `portfolio_executive.xlsx` |
| PDF | `governance_run_summary.pdf`, `audit_events.pdf`, `portfolio_executive.pdf` |

## Implementation

- **XLSX:** `app/services/report_xlsx.py` (openpyxl)
- **PDF:** `app/services/report_pdf.py` (reportlab)
- **Router:** `app/routers/reports.py`
- **UI:** Reports → Exports tab in `WorkspaceReportsPage.tsx`

## Frontend download flow

The Exports tab calls `fetchRunSummaryReport`, `fetchAuditExport`, and `fetchPortfolioExecutiveExport` with `format` set to `xlsx` or `pdf`. Binary responses are saved via `Blob` + anchor download.
