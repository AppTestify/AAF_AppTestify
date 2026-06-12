# Workspace UI Refinement

Epic: [CAS-129](https://apptestify.atlassian.net/browse/CAS-129) — UI Workspace Refinement (Dashboards, Reports & Design System)

This document describes the frontend architecture introduced across UI sprints S1–S6 for the Casantris workspace.

## Page shell

All workspace routes use `WorkspacePageShell` (`frontend/src/components/layout/WorkspacePageShell.tsx`):

- **Variants:** `governance` (Command Center, Ask AI) and `operational` (Runs, Cases, Evidence, Settings).
- **Props:** `eyebrow`, `title`, `subtitle`, optional `actions`, and `dashboard` for full-width Command Center layout.
- **CSS:** `.workspace-page` in `frontend/src/styles/layout.css` aligns max-width and padding with the app shell.

## Shared UI primitives

| Component | Path | Role |
|-----------|------|------|
| `KpiStrip` | `components/ui/KpiStrip.tsx` | Metric row with tone variants; supports skeleton loading |
| `DataTable` | `components/ui/DataTable.tsx` | Column-driven table with empty state and skeleton rows |
| `PaginationBar` | `components/ui/PaginationBar.tsx` | Offset pagination with human-readable range copy |
| `SectionCard` | `components/ui/SectionCard.tsx` | Card wrapper for report sections |
| `SegmentedTabs` | `components/ui/SegmentedTabs.tsx` | Unified tab control for Settings, Reports, etc. |
| `EmptyState` | `components/ui/EmptyState.tsx` | Empty list placeholder with optional CTA |

Styles are split under `frontend/src/styles/` (`buttons.css`, `layout.css`, `tables.css`, `charts.css`) and imported from `App.css`.

## Charts

Charts live in `frontend/src/components/charts/` and use **Recharts** with theme tokens from `ChartTheme.tsx` (`useChartColors`, `statusColor`, `ChartCard`).

### Command Center (S2 + S6)

**Row 1 — distribution**

- `RunStatusDonut` — run status counts from `fetchDashboardSummary()`
- `CaseStatusBar` — case status counts
- `ConnectorHealthDonut` — connector validation health

**Row 2 — timeseries & observability (S6)**

- `RunsTrendLine` — daily run counts by status from `GET /telemetry/runs-timeseries?days=7`
- `SloBurnChart` — short/long SLO burn from `fetchObservabilitySummary()`
- `LlmCostBar` — OK vs degraded LLM invocations from observability summary

Chart data mappers in `frontend/src/lib/chartMappers.ts` normalize API payloads for Recharts.

### Drill-down (S6)

Interactive chart segments navigate to filtered list pages via React Router, e.g.:

- Run status → `/app/runs?status=failed`
- Fallback tables expose the same links as accessible buttons (`.chart-drill-link`).

Each chart includes an `aria-label` and a semantic HTML fallback table for screen readers.

## Pagination contract (S4)

List APIs return paginated envelopes:

```json
{ "items": [...], "total": 237, "limit": 50, "offset": 0 }
```

Frontend types: `PaginatedResponse<T>` in `frontend/src/api.ts`.

`PaginationBar` displays **"51–100 of 237"** (not raw offset). Runs and Cases pages sync `page` and `page_size` query params with the bar.

## Loading & accessibility (S6)

- `KpiStrip` and `DataTable` render shimmer skeletons while data loads (`aria-busy`).
- Disabled navigation in Ask AI uses real `<button disabled>` instead of styled `<Link>` hacks (`GovernanceView.tsx`).

## Tests

Vitest coverage (extends CAS-53):

- `components/ui/PaginationBar.test.tsx` — range copy, disabled states, navigation
- `lib/chartMappers.test.ts` — status and timeseries mapping utilities

Run: `npm test` in `frontend/`.

## Related work

- **CAS-100** — Phase 1 decision flow UI
- **CAS-115** — Phase 3 decision flow UI
- **CAS-53** — Frontend vitest baseline
