import { useEffect, useMemo, useState } from "react";
import {
  fetchAuditEvents,
  fetchAuditExport,
  fetchConsensusSummary,
  fetchExecutiveSummaries,
  fetchExecutivePortfolioReport,
  fetchGovernanceRuns,
  fetchIntelligenceIncidents,
  fetchReleaseGovernance,
  fetchRunSummaryReport,
  fetchWorkflowRuns,
  type AuditEvent,
  type ConsensusSummary,
  type ExecutiveSummary,
  type ExecutivePortfolioReport,
  type GovernanceRunV1,
  type IntelligenceIncident,
  type ReleaseGovernance,
  type WorkflowRun,
} from "../api";
import { IncidentFindingsPanel } from "../components/IncidentFindingsPanel";

type WorkspaceReportsPageProps = {
  };

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function WorkspaceReportsPage({}: WorkspaceReportsPageProps) {
  const [loading, setLoading] = useState(false);
  const [runs, setRuns] = useState<GovernanceRunV1[]>([]);
  const [incidents, setIncidents] = useState<IntelligenceIncident[]>([]);
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRun[]>([]);
  const [execSummaries, setExecSummaries] = useState<ExecutiveSummary[]>([]);
  const [auditRows, setAuditRows] = useState<AuditEvent[]>([]);
  const [consensus, setConsensus] = useState<ConsensusSummary | null>(null);
  const [releaseGov, setReleaseGov] = useState<ReleaseGovernance | null>(null);
  const [portfolioReport, setPortfolioReport] = useState<ExecutivePortfolioReport | null>(null);
  const [output, setOutput] = useState<string>("");
  const [toast, setToast] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [runStatusFilter, setRunStatusFilter] = useState<string>("");
  const [auditAreaFilter, setAuditAreaFilter] = useState<string>("");

  const notify = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 2200);
  };

  useEffect(() => {
    setLoading(true);
    setError("");
    Promise.all([
      fetchGovernanceRuns({ limit: 200 }),
      fetchIntelligenceIncidents(100),
      fetchWorkflowRuns(),
      fetchExecutiveSummaries(25),
      fetchAuditEvents({ limit: 500 }),
      fetchConsensusSummary(),
      fetchReleaseGovernance(),
      fetchExecutivePortfolioReport(),
    ])
      .then(([r, i, w, e, a, c, g, p]) => {
        setRuns(r);
        setIncidents(i);
        setWorkflowRuns(w);
        setExecSummaries(e);
        setAuditRows(a);
        setConsensus(c);
        setReleaseGov(g);
        setPortfolioReport(p);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load reports"))
      .finally(() => setLoading(false));
  }, []);

  const runStatusCounts = useMemo(() => {
    const out: Record<string, number> = {};
    for (const r of runs) out[r.status] = (out[r.status] ?? 0) + 1;
    return out;
  }, [runs]);

  const severityCounts = useMemo(() => {
    const out: Record<string, number> = {};
    for (const i of incidents) out[i.severity] = (out[i.severity] ?? 0) + 1;
    return out;
  }, [incidents]);

  const workflowTypeCounts = useMemo(() => {
    const out: Record<string, number> = {};
    for (const w of workflowRuns) out[w.workflow_type] = (out[w.workflow_type] ?? 0) + 1;
    return out;
  }, [workflowRuns]);

  const exportRunsJson = async () => {
    try {
      setError("");
      const data = (await fetchRunSummaryReport("json", 200, runStatusFilter || undefined)) as {
        count: number;
        items: Record<string, unknown>[];
      };
      setOutput(JSON.stringify(data, null, 2));
      notify(`Loaded ${data.count} run summary rows`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run summary failed");
    }
  };

  const exportRunsCsv = async () => {
    try {
      setError("");
      const blob = (await fetchRunSummaryReport("csv", 200, runStatusFilter || undefined)) as Blob;
      downloadBlob(blob, "governance_run_summary.csv");
      notify("Run summary CSV downloaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "CSV export failed");
    }
  };

  const copyWorkspaceLink = (path: string) => {
    const url = `${window.location.origin}${path}`;
    void navigator.clipboard.writeText(url);
    notify("Link copied — recipients need workspace sign-in");
  };

  const exportAuditJson = async () => {
    try {
      setError("");
      const data = (await fetchAuditExport("json", auditAreaFilter || undefined)) as {
        count: number;
        items: Record<string, unknown>[];
      };
      setOutput(JSON.stringify(data, null, 2));
      notify(`Loaded ${data.count} audit rows`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Audit export failed");
    }
  };

  const exportAuditCsv = async () => {
    try {
      setError("");
      const blob = (await fetchAuditExport("csv", auditAreaFilter || undefined)) as Blob;
      downloadBlob(blob, "audit_events.csv");
      notify("Audit CSV downloaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Audit CSV export failed");
    }
  };

  return (
    <div className="app">
      <header className="app-header workspace-page-head">
        <div className="brand">
          <h1>Reports</h1>
          <span>Comprehensive operational, intelligence, workflow, and audit reporting center</span>
        </div>
      </header>
      {toast ? <div className="alert alert-success">{toast}</div> : null}
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      {loading ? <div className="card">Loading reports…</div> : null}
      {!loading ? (
        <div className="workspace-kpi-strip">
          <div className="metric">
            <div className="label">Total runs</div>
            <div className="value">{runs.length}</div>
          </div>
          <div className="metric">
            <div className="label">Incidents</div>
            <div className="value warn">{incidents.length}</div>
          </div>
          <div className="metric">
            <div className="label">Workflow runs</div>
            <div className="value">{workflowRuns.length}</div>
          </div>
          <div className="metric">
            <div className="label">Executive summaries</div>
            <div className="value">{execSummaries.length}</div>
          </div>
          <div className="metric">
            <div className="label">Audit events</div>
            <div className="value">{auditRows.length}</div>
          </div>
          <div className="metric">
            <div className="label">Avg consensus</div>
            <div className="value">{consensus ? consensus.avg_consensus_score.toFixed(2) : "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Release decision</div>
            <div className="value">{releaseGov?.decision ?? "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Portfolio projects</div>
            <div className="value">{portfolioReport?.projects_total ?? "..."}</div>
          </div>
        </div>
      ) : null}
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Executive portfolio report</h2>
            <p>Cross-project release readiness and decision posture for leadership governance.</p>
          </div>
        </div>
        <div className="workspace-kpi-strip">
          <div className="metric"><div className="label">Releases total</div><div className="value">{portfolioReport?.releases_total ?? 0}</div></div>
          <div className="metric"><div className="label">Approved</div><div className="value good">{portfolioReport?.releases_approved ?? 0}</div></div>
          <div className="metric"><div className="label">Blocked</div><div className="value warn">{portfolioReport?.releases_blocked ?? 0}</div></div>
          <div className="metric"><div className="label">High risk</div><div className="value warn">{portfolioReport?.high_risk_open ?? 0}</div></div>
          <div className="metric"><div className="label">Avg confidence</div><div className="value">{(((portfolioReport?.avg_confidence ?? 0) * 100)).toFixed(1)}%</div></div>
        </div>
      </div>
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Share workspace destinations</h2>
            <p>Copy links for teammates with tenant access. Exports below remain the portable artifacts (CSV/JSON).</p>
          </div>
        </div>
        <div className="actions" style={{ flexWrap: "wrap", gap: "0.5rem" }}>
          <button className="btn btn-ghost" type="button" onClick={() => copyWorkspaceLink("/app/reports")}>
            Copy link to Reports
          </button>
          <button className="btn btn-ghost" type="button" onClick={() => copyWorkspaceLink("/app/runs")}>
            Copy link to Runs
          </button>
          <button className="btn btn-ghost" type="button" onClick={() => copyWorkspaceLink("/app/dashboard")}>
            Copy link to Dashboard
          </button>
        </div>
      </div>
      <div className="card-group">
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Run summary export</h2>
            <p>Filter run-level outcomes, inspect JSON, or download governance summary CSV (includes orchestration vs findings columns).</p>
          </div>
        </div>
        <div className="workspace-toolbar">
          <div className="form-row">
            <label htmlFor="report-run-status">Run status</label>
            <select id="report-run-status" value={runStatusFilter} onChange={(e) => setRunStatusFilter(e.target.value)}>
              <option value="">All</option>
              <option value="queued">Queued</option>
              <option value="running">Running</option>
              <option value="succeeded">Succeeded</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>
        <div className="actions">
          <button className="btn btn-ghost" type="button" onClick={exportRunsJson}>
            View JSON
          </button>
          <button className="btn btn-primary" type="button" onClick={exportRunsCsv}>
            Download CSV
          </button>
        </div>
      </div>
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Audit export</h2>
            <p>Query audit events by area and extract JSON/CSV for compliance trails.</p>
          </div>
        </div>
        <div className="workspace-toolbar">
          <div className="form-row">
            <label htmlFor="report-audit-area">Area filter</label>
            <input
              id="report-audit-area"
              value={auditAreaFilter}
              onChange={(e) => setAuditAreaFilter(e.target.value)}
              placeholder="e.g. governance_run"
            />
          </div>
        </div>
        <div className="actions">
          <button className="btn btn-ghost" type="button" onClick={exportAuditJson}>
            View JSON
          </button>
          <button className="btn btn-primary" type="button" onClick={exportAuditCsv}>
            Download CSV
          </button>
        </div>
      </div>
      </div>
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Operational distribution</h2>
            <p>Cross-cut counts by run status, incident severity, and workflow type.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Report dimension</th>
                <th>Value</th>
                <th>Count</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(runStatusCounts).map(([k, v]) => (
                <tr key={`run-${k}`}>
                  <td>Run status</td>
                  <td>{k}</td>
                  <td>{v}</td>
                </tr>
              ))}
              {Object.entries(severityCounts).map(([k, v]) => (
                <tr key={`sev-${k}`}>
                  <td>Incident severity</td>
                  <td>{k}</td>
                  <td>{v}</td>
                </tr>
              ))}
              {Object.entries(workflowTypeCounts).map(([k, v]) => (
                <tr key={`wf-${k}`}>
                  <td>Workflow type</td>
                  <td>{k}</td>
                  <td>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Incident intelligence report</h2>
            <p>Top correlated incidents with confidence and consensus indicators.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Incident</th>
                <th>Severity</th>
                <th>Consensus</th>
                <th>Confidence</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {incidents.slice(0, 25).map((i) => (
                <tr key={i.id}>
                  <td>{i.title}</td>
                  <td>{i.severity}</td>
                  <td>{i.consensus_score.toFixed(2)}</td>
                  <td>{i.confidence.toFixed(2)}</td>
                  <td>{i.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {incidents.slice(0, 5).map((incident) => (
          <details key={`findings-${incident.id}`} className="accordion" style={{ marginTop: "0.75rem" }}>
            <summary>
              Agent findings — {incident.title.slice(0, 72)}
              {incident.title.length > 72 ? "…" : ""}
            </summary>
            <IncidentFindingsPanel incident={incident} />
          </details>
        ))}
      </div>
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Workflow outcomes report</h2>
            <p>Decision quality and completion status across workflow execution types.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Workflow</th>
                <th>Decision</th>
                <th>Score</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {workflowRuns.slice(0, 25).map((w) => (
                <tr key={w.id}>
                  <td>{w.workflow_type}</td>
                  <td>{w.decision ?? "-"}</td>
                  <td>{w.score.toFixed(2)}</td>
                  <td>{w.status}</td>
                  <td>{new Date(w.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Executive summaries report</h2>
            <p>Leadership-ready narratives with XI scoring and timeline context.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Type</th>
                <th>XI score</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {execSummaries.slice(0, 25).map((s) => (
                <tr key={s.id}>
                  <td>{s.title}</td>
                  <td>{s.summary_type}</td>
                  <td>{s.xi_score.toFixed(2)}</td>
                  <td>{new Date(s.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {output ? (
        <div className="card">
          <div className="workspace-section-intro">
            <div>
              <h2>Export preview</h2>
              <p>Rendered output for quick validation before sharing.</p>
            </div>
          </div>
          <pre className="json-preview" style={{ maxHeight: 420 }}>{output}</pre>
        </div>
      ) : null}
    </div>
  );
}
