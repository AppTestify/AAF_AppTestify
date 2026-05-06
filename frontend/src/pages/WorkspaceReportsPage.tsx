import { useEffect, useMemo, useState } from "react";
import {
  fetchAuditEvents,
  fetchAuditExport,
  fetchConsensusSummary,
  fetchExecutiveSummaries,
  fetchGovernanceRuns,
  fetchIntelligenceIncidents,
  fetchReleaseGovernance,
  fetchRunSummaryReport,
  fetchWorkflowRuns,
  type AuditEvent,
  type ConsensusSummary,
  type ExecutiveSummary,
  type GovernanceRunV1,
  type IntelligenceIncident,
  type ReleaseGovernance,
  type WorkflowRun,
} from "../api";

type WorkspaceReportsPageProps = {
  token: string;
};

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function WorkspaceReportsPage({ token }: WorkspaceReportsPageProps) {
  const [loading, setLoading] = useState(false);
  const [runs, setRuns] = useState<GovernanceRunV1[]>([]);
  const [incidents, setIncidents] = useState<IntelligenceIncident[]>([]);
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRun[]>([]);
  const [execSummaries, setExecSummaries] = useState<ExecutiveSummary[]>([]);
  const [auditRows, setAuditRows] = useState<AuditEvent[]>([]);
  const [consensus, setConsensus] = useState<ConsensusSummary | null>(null);
  const [releaseGov, setReleaseGov] = useState<ReleaseGovernance | null>(null);
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
      fetchGovernanceRuns(token, { limit: 200 }),
      fetchIntelligenceIncidents(token, 100),
      fetchWorkflowRuns(token),
      fetchExecutiveSummaries(token, 25),
      fetchAuditEvents(token, { limit: 500 }),
      fetchConsensusSummary(token),
      fetchReleaseGovernance(token),
    ])
      .then(([r, i, w, e, a, c, g]) => {
        setRuns(r);
        setIncidents(i);
        setWorkflowRuns(w);
        setExecSummaries(e);
        setAuditRows(a);
        setConsensus(c);
        setReleaseGov(g);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load reports"))
      .finally(() => setLoading(false));
  }, [token]);

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
      const data = (await fetchRunSummaryReport(token, "json", 200, runStatusFilter || undefined)) as {
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
      const blob = (await fetchRunSummaryReport(token, "csv", 200, runStatusFilter || undefined)) as Blob;
      downloadBlob(blob, "governance_run_summary.csv");
      notify("Run summary CSV downloaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "CSV export failed");
    }
  };

  const exportAuditJson = async () => {
    try {
      setError("");
      const data = (await fetchAuditExport(token, "json", auditAreaFilter || undefined)) as {
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
      const blob = (await fetchAuditExport(token, "csv", auditAreaFilter || undefined)) as Blob;
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
        <div className="metrics">
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
        </div>
      ) : null}
      <div className="card">
        <h2>Run summary</h2>
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
        <h2>Operational distribution</h2>
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
        <h2>Incident intelligence report</h2>
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
      </div>
      <div className="card">
        <h2>Workflow outcomes report</h2>
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
        <h2>Executive summaries report</h2>
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
      <div className="card">
        <h2>Audit events</h2>
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
      {output ? (
        <div className="card">
          <h2>Preview</h2>
          <pre className="json-preview" style={{ maxHeight: 420 }}>{output}</pre>
        </div>
      ) : null}
    </div>
  );
}
