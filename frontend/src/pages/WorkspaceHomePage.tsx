import { useEffect, useState } from "react";
import {
  fetchConsensusSummary,
  fetchDashboardSummary,
  fetchExecutiveSummaries,
  fetchWorkflowRuns,
  fetchIntelligenceIncidents,
  fetchObservabilitySummary,
  fetchReleaseGovernance,
  runGovernanceWorkflow,
  runRarIteration,
  type ConsensusSummary,
  type DashboardSummary,
  type ExecutiveSummary,
  type IntelligenceIncident,
  type ObservabilitySummary,
  type ReleaseGovernance,
  type UserPublic,
  type WorkflowRun,
} from "../api";

type WorkspaceHomePageProps = {
  token: string;
  user: UserPublic;
};

export function WorkspaceHomePage({ token, user }: WorkspaceHomePageProps) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [obs, setObs] = useState<ObservabilitySummary | null>(null);
  const [consensus, setConsensus] = useState<ConsensusSummary | null>(null);
  const [incidents, setIncidents] = useState<IntelligenceIncident[]>([]);
  const [execSummaries, setExecSummaries] = useState<ExecutiveSummary[]>([]);
  const [releaseGov, setReleaseGov] = useState<ReleaseGovernance | null>(null);
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchDashboardSummary(token),
      fetchObservabilitySummary(token),
      fetchConsensusSummary(token),
      fetchIntelligenceIncidents(token, 6),
      fetchExecutiveSummaries(token, 3),
      fetchReleaseGovernance(token),
      fetchWorkflowRuns(token),
    ])
      .then(([a, b, c, d, e, f, g]) => {
        setSummary(a);
        setObs(b);
        setConsensus(c);
        setIncidents(d);
        setExecSummaries(e);
        setReleaseGov(f);
        setWorkflowRuns(g);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load dashboard"));
  }, [token]);

  const runWorkflow = async (workflowType: string) => {
    try {
      const latestIncident = incidents[0];
      const out = await runGovernanceWorkflow(token, workflowType, latestIncident?.id);
      setWorkflowRuns((prev) => [out, ...prev].slice(0, 10));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Workflow execution failed");
    }
  };

  const rerunRar = async () => {
    try {
      const latestIncident = incidents[0];
      if (!latestIncident) return;
      const rerun = await runRarIteration(token, latestIncident.id);
      setIncidents((prev) =>
        prev.map((i) => (i.id === latestIncident.id ? { ...i, confidence: rerun.confidence_after } : i))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "RAR run failed");
    }
  };

  const maxRunCount = Math.max(1, ...Object.values(summary?.run_status_counts ?? { empty: 1 }));
  const maxCaseCount = Math.max(1, ...Object.values(summary?.case_status_counts ?? { empty: 1 }));

  return (
    <div className="app dashboard-page">
      <header className="app-header dashboard-header">
        <div className="brand">
          <h1>Enterprise Operations Dashboard</h1>
          <span>Decision-ready governance posture with execution and risk intelligence</span>
        </div>
      </header>
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      <section className="dashboard-section">
        <div className="dashboard-section-head">
          <h2>Executive snapshot</h2>
          <p>Core platform posture across delivery, reliability, and risk in the last 24 hours.</p>
        </div>
        <div className="metrics dashboard-kpis">
          <div className="metric">
            <div className="label">Runs (24h)</div>
            <div className="value">{summary?.runs_24h ?? "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Success (24h)</div>
            <div className="value good">{summary?.runs_success_24h ?? "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Open cases</div>
            <div className="value warn">{summary?.cases_open ?? "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Alerts (24h)</div>
            <div className="value bad">{summary?.alerts_24h ?? "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Req/min</div>
            <div className="value">{obs?.requests_per_min ?? "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Latency p95</div>
            <div className="value">{obs ? `${obs.latency_ms_p95} ms` : "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Error rate</div>
            <div className="value bad">{obs ? `${(obs.error_rate * 100).toFixed(2)}%` : "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Consensus score</div>
            <div className="value">{consensus ? consensus.avg_consensus_score.toFixed(2) : "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Open high risk</div>
            <div className="value warn">{consensus?.high_risk_open ?? "..."}</div>
          </div>
        </div>
      </section>

      <section className="dashboard-section">
        <div className="dashboard-section-head">
          <h2>Decision posture</h2>
          <p>Release readiness and real-time operational pressure signals for high-impact decisions.</p>
        </div>
        <div className="dashboard-grid dashboard-grid-two">
          <div className="card dashboard-card-emphasis">
            <h2>Release governance</h2>
            <div className="settings-grid">
              <div className="metric">
                <div className="label">Decision</div>
                <div className="value">{releaseGov?.decision ?? "..."}</div>
              </div>
              <div className="metric">
                <div className="label">Risk level</div>
                <div className="value warn">{releaseGov?.risk_level ?? "..."}</div>
              </div>
              <div className="metric">
                <div className="label">Consensus</div>
                <div className="value">{releaseGov ? releaseGov.consensus_score.toFixed(2) : "..."}</div>
              </div>
            </div>
            <p className="field-hint">{releaseGov?.reason ?? "..."}</p>
          </div>

          <div className="card dashboard-card-emphasis">
            <h2>Operational pressure</h2>
            <div className="settings-grid">
              <div className="metric">
                <div className="label">In-flight requests</div>
                <div className="value warn">{obs?.inflight_requests ?? "..."}</div>
              </div>
              <div className="metric">
                <div className="label">Run queue depth</div>
                <div className="value warn">{obs?.run_queue_depth ?? "..."}</div>
              </div>
              <div className="metric">
                <div className="label">Run p95 latency</div>
                <div className="value">{obs ? `${obs.run_latency_ms_p95} ms` : "..."}</div>
              </div>
              <div className="metric">
                <div className="label">Runs retried</div>
                <div className="value">{obs?.runs_retried ?? "..."}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="dashboard-section">
        <div className="dashboard-section-head">
          <h2>Operational insights</h2>
          <p>Delivery distribution, incident intelligence, and immediate corrective actions.</p>
        </div>
        <div className="card">
          <h2>Delivery posture</h2>
          <div className="settings-grid delivery-posture-grid">
            <div className="metric">
              <div className="label">Connectors enabled</div>
              <div className="value">{summary ? `${summary.connectors_enabled}/${summary.connectors_total}` : "..."}</div>
            </div>
            <div className="metric">
              <div className="label">Providers enabled</div>
              <div className="value">{summary ? `${summary.providers_enabled}/${summary.providers_total}` : "..."}</div>
            </div>
            <div className="metric">
              <div className="label">Integration coverage</div>
              <div className="value">{summary ? `${summary.integration_coverage_pct}%` : "..."}</div>
            </div>
            <div className="metric">
              <div className="label">Integration freshness</div>
              <div className="value">{summary ? `${summary.integration_fresh_pct}%` : "..."}</div>
            </div>
          </div>
        </div>

        <div className="dashboard-grid">
          <div className="card">
            <h2>Run status graph</h2>
            <div className="chart-list">
              {Object.entries(summary?.run_status_counts ?? {}).map(([k, v]) => (
                <div key={k} className="chart-row">
                  <div className="chart-label">{k}</div>
                  <div className="chart-bar-wrap">
                    <div className={`chart-bar ${k}`} style={{ width: `${(v / maxRunCount) * 100}%` }} />
                  </div>
                  <div className="chart-value">{v}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h2>Case status graph</h2>
            <div className="chart-list">
              {Object.entries(summary?.case_status_counts ?? {}).map(([k, v]) => (
                <div key={k} className="chart-row">
                  <div className="chart-label">{k}</div>
                  <div className="chart-bar-wrap">
                    <div className={`chart-bar ${k}`} style={{ width: `${(v / maxCaseCount) * 100}%` }} />
                  </div>
                  <div className="chart-value">{v}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h2>Executive summaries</h2>
            <ul className="list-plain">
              {execSummaries.map((s) => (
                <li key={s.id}>
                  <span className="status-chip succeeded">XI {s.xi_score.toFixed(2)}</span> {s.content}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="card">
          <div className="dashboard-card-toolbar">
            <h2>Cross-agent incidents</h2>
            <div className="actions">
              <button className="btn btn-ghost" type="button" onClick={rerunRar} disabled={!incidents.length}>
                RAR Re-analyze top incident
              </button>
              <button className="btn btn-ghost" type="button" onClick={() => runWorkflow("cost_spike")}>
                Run cost spike workflow
              </button>
              <button className="btn btn-ghost" type="button" onClick={() => runWorkflow("security_governance")}>
                Run security workflow
              </button>
              <button className="btn btn-ghost" type="button" onClick={() => runWorkflow("post_incident_review")}>
                Run post-incident review
              </button>
            </div>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Severity</th>
                  <th>Consensus</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((i) => (
                  <tr key={i.id}>
                    <td>{i.title}</td>
                    <td>
                      <span className={`status-chip ${i.severity === "critical" ? "failed" : "running"}`}>{i.severity}</span>
                    </td>
                    <td>{i.consensus_score.toFixed(2)}</td>
                    <td>{i.confidence.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="dashboard-section">
        <div className="dashboard-section-head">
          <h2>Execution traceability</h2>
          <p>Workflow outcomes, run history, alert stream, and endpoint pressure in one operational view.</p>
        </div>
        <div className="dashboard-grid dashboard-grid-two">
          <div className="card">
            <h2>Workflow runs</h2>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Workflow</th>
                    <th>Decision</th>
                    <th>Score</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {workflowRuns.map((w) => (
                    <tr key={w.id}>
                      <td>{w.workflow_type}</td>
                      <td>{w.decision ?? "-"}</td>
                      <td>{w.score.toFixed(2)}</td>
                      <td>{new Date(w.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <h2>Recent runs and readiness context</h2>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Status</th>
                    <th>Prompt</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {(summary?.recent_runs ?? []).map((run) => (
                    <tr key={run.id}>
                      <td>#{run.id}</td>
                      <td>
                        <span className={`status-chip ${run.status}`}>{run.status}</span>
                      </td>
                      <td className="mono">{run.prompt}</td>
                      <td>{new Date(run.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="dashboard-grid dashboard-grid-two">
          <div className="card">
            <h2>Alerts stream</h2>
            <ul className="list-plain">
              {(summary?.recent_alerts ?? []).map((e) => (
                <li key={e.id}>
                  <span className={`status-chip ${e.severity === "critical" ? "failed" : "running"}`}>{e.severity}</span>{" "}
                  <span className="mono">
                    {e.area}/{e.action}
                  </span>{" "}
                  {e.summary}
                </li>
              ))}
            </ul>
          </div>

          <div className="card">
            <h2>Hot endpoints</h2>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Endpoint</th>
                    <th>Requests</th>
                    <th>Errors</th>
                  </tr>
                </thead>
                <tbody>
                  {(obs?.endpoints_top ?? []).map((row) => (
                    <tr key={row.endpoint}>
                      <td className="mono">{row.endpoint}</td>
                      <td>{row.count}</td>
                      <td>{row.errors}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
