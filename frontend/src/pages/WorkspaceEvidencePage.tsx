import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  fetchEvidence,
  fetchGovernanceRun,
  fetchGovernanceRuns,
  fetchPortfolioProjects,
  type EvidenceRow,
  type PortfolioProject,
} from "../api";
import { EvidenceSourceCards } from "../components/governance/EvidenceSourceCards";
import { GovernanceFlowStepper } from "../components/governance/GovernanceFlowStepper";
import { EvidenceTimelineTable } from "../components/governance/EvidenceTimelineTable";
import { WorkspacePageShell } from "../components/layout/WorkspacePageShell";
import { PaginationBar } from "../components/ui/PaginationBar";
import { useDashboardSummary } from "../hooks/useDashboardSummary";
import {
  deriveConnectorSummaries,
  deriveEvidenceTimeline,
  formatRelativeTime,
  parseGovernanceRunResult,
  type ParsedRunContext,
} from "../lib/governancePresentation";

export function WorkspaceEvidencePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const listProjectFilter = searchParams.get("portfolio_project_id") ?? "";
  const runIdParam = searchParams.get("run_id") ?? "";

  const setListProjectFilter = (v: string) => {
    const next = new URLSearchParams(searchParams);
    if (v) next.set("portfolio_project_id", v);
    else next.delete("portfolio_project_id");
    setSearchParams(next, { replace: true });
  };

  const syncRunIdToUrl = (v: string) => {
    const next = new URLSearchParams(searchParams);
    if (v.trim()) next.set("run_id", v.trim());
    else next.delete("run_id");
    setSearchParams(next, { replace: true });
  };

  const [rows, setRows] = useState<EvidenceRow[]>([]);
  const [evidenceTotal, setEvidenceTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [projects, setProjects] = useState<PortfolioProject[]>([]);
  const [connector, setConnector] = useState<string>("");
  const [runId, setRunId] = useState<string>(runIdParam);
  const [selected, setSelected] = useState<EvidenceRow | null>(null);
  const [error, setError] = useState<string>("");
  const [listLoading, setListLoading] = useState(false);
  const [parsedRun, setParsedRun] = useState<ParsedRunContext | null>(null);
  const { summary: dashboardSummary } = useDashboardSummary();
  const connectorHealth = dashboardSummary?.connector_health ?? null;

  useEffect(() => {
    setRunId(runIdParam);
  }, [runIdParam]);

  useEffect(() => {
    fetchPortfolioProjects()
      .then(setProjects)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load portfolio projects"));
    fetchGovernanceRuns({ status: "succeeded", limit: 1 })
      .then(async (page) => {
        const id = runIdParam ? Number(runIdParam) : page.items[0]?.id;
        if (id && Number.isFinite(id)) {
          const full = await fetchGovernanceRun(id);
          setParsedRun(parseGovernanceRunResult(full));
        }
      })
      .catch(() => setParsedRun(null));
  }, [runIdParam]);

  useEffect(() => {
    setOffset(0);
  }, [connector, runId, listProjectFilter]);

  useEffect(() => {
    setListLoading(true);
    fetchEvidence({
      connector: connector || undefined,
      run_id: runId ? Number(runId) : undefined,
      portfolio_project_id: listProjectFilter ? Number(listProjectFilter) : undefined,
      limit: pageSize,
      offset,
    })
      .then((page) => {
        setRows(page.items);
        setEvidenceTotal(page.total);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load evidence"))
      .finally(() => setListLoading(false));
  }, [connector, runId, listProjectFilter, offset, pageSize]);

  const connectorOrder = (parsedRun?.result.intent?.connectors as string[] | undefined) ?? [];
  const prompt = parsedRun?.run.prompt ?? "";
  const sortOptions = { prompt, connectorOrder };
  const sourceCards = deriveConnectorSummaries(parsedRun, connectorHealth, sortOptions);
  const timeline = deriveEvidenceTimeline(rows, parsedRun?.result.normalized_evidence ?? [], sortOptions);
  const jiraRecord = parsedRun?.result.normalized_evidence?.find((e) => e.source === "jira");
  const jiraBaseUrl =
    typeof jiraRecord?.metadata?.jira_base_url === "string" ? jiraRecord.metadata.jira_base_url : null;
  const refreshedLabel = rows[0] ? `Refreshed ${formatRelativeTime(rows[0].created_at)}` : undefined;

  const evidenceStats = useMemo(() => {
    const byConnector = rows.reduce<Record<string, number>>((acc, row) => {
      acc[row.connector_name] = (acc[row.connector_name] ?? 0) + 1;
      return acc;
    }, {});
    return {
      total: rows.length,
      connectors: Object.keys(byConnector).length,
    };
  }, [rows]);

  return (
    <WorkspacePageShell
      variant="governance"
      eyebrow="Evidence Hub"
      title="Live signals from GitHub, Jira, and FinOps"
      subtitle="Every governance decision is grounded in fresh evidence pulled from the systems your teams already use."
    >
      {parsedRun ? <GovernanceFlowStepper runId={parsedRun.run.id} activeStep="evidence" /> : null}

      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}

      <EvidenceSourceCards cards={sourceCards} />

      <div className="workspace-toolbar">
        <div className="form-row">
          <label htmlFor="connector-filter">Connector</label>
          <input id="connector-filter" value={connector} onChange={(e) => setConnector(e.target.value)} placeholder="github" />
        </div>
        <div className="form-row">
          <label htmlFor="run-filter">Run ID</label>
          <input
            id="run-filter"
            value={runId}
            onChange={(e) => {
              setRunId(e.target.value);
              syncRunIdToUrl(e.target.value);
            }}
            placeholder="e.g. 12"
          />
        </div>
        <div className="form-row">
          <label htmlFor="evidence-project-filter">Project</label>
          <select id="evidence-project-filter" value={listProjectFilter} onChange={(e) => setListProjectFilter(e.target.value)}>
            <option value="">All projects</option>
            {projects.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.key} — {p.name}
              </option>
            ))}
          </select>
        </div>
        <span className="workspace-meta">
          {evidenceTotal} rows · {evidenceStats.connectors} connectors on this page
        </span>
      </div>

      {listLoading ? <div className="table-skeleton" /> : null}
      <EvidenceTimelineTable rows={timeline} refreshedLabel={refreshedLabel} jiraBaseUrl={jiraBaseUrl} />

      {selected ? (
        <div className="card" style={{ marginTop: "1rem" }}>
          <h2>Snapshot detail #{selected.id}</h2>
          <pre className="json-preview">{JSON.stringify(selected.payload_json, null, 2)}</pre>
        </div>
      ) : null}

      <div className="card" style={{ marginTop: "1rem" }}>
        <h2>Raw evidence rows</h2>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Connector</th>
                <th>Run</th>
                <th>Captured</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} onClick={() => setSelected(r)} className={selected?.id === r.id ? "row-selected" : ""}>
                  <td>#{r.id}</td>
                  <td>{r.connector_name}</td>
                  <td>#{r.run_id}</td>
                  <td>{new Date(r.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <PaginationBar
          offset={offset}
          pageSize={pageSize}
          itemCount={rows.length}
          totalCount={evidenceTotal}
          onOffsetChange={setOffset}
          onPageSizeChange={setPageSize}
        />
      </div>
    </WorkspacePageShell>
  );
}
