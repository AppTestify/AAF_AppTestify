import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchCases,
  fetchConsensusSummary,
  fetchDashboardSummary,
  fetchExecutiveSummaries,
  fetchGovernanceRun,
  fetchGovernanceRuns,
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
  type GovernanceCase,
  type WorkflowRun,
} from "../api";
import { AIRecommendationCard } from "../components/governance/AIRecommendationCard";
import { DecisionFlowTrace } from "../components/governance/DecisionFlowTrace";
import { RecentDecisionsList } from "../components/governance/RecentDecisionsList";
import { RiskMetricCard } from "../components/governance/RiskMetricCard";
import { IncidentFindingsPanel } from "../components/IncidentFindingsPanel";
import {
  deriveDecisionFlow,
  deriveRecentDecisions,
  deriveRecommendation,
  deriveRiskCards,
  isLiveTrace,
  parseGovernanceRunResult,
  type ParsedRunContext,
} from "../lib/governancePresentation";

type WorkspaceHomePageProps = {
  user: UserPublic;
};

export function WorkspaceHomePage({}: WorkspaceHomePageProps) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [obs, setObs] = useState<ObservabilitySummary | null>(null);
  const [consensus, setConsensus] = useState<ConsensusSummary | null>(null);
  const [incidents, setIncidents] = useState<IntelligenceIncident[]>([]);
  const [execSummaries, setExecSummaries] = useState<ExecutiveSummary[]>([]);
  const [releaseGov, setReleaseGov] = useState<ReleaseGovernance | null>(null);
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRun[]>([]);
  const [parsedRun, setParsedRun] = useState<ParsedRunContext | null>(null);
  const [cases, setCases] = useState<GovernanceCase[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    Promise.all([
      fetchDashboardSummary(),
      fetchObservabilitySummary(),
      fetchConsensusSummary(),
      fetchIntelligenceIncidents(6),
      fetchExecutiveSummaries(3),
      fetchReleaseGovernance(),
      fetchWorkflowRuns(),
      fetchCases(20),
      fetchGovernanceRuns({ status: "succeeded", limit: 1 }),
    ])
      .then(async ([a, b, c, d, e, f, g, caseRows, runs]) => {
        setSummary(a);
        setObs(b);
        setConsensus(c);
        setIncidents(d);
        setExecSummaries(e);
        setReleaseGov(f);
        setWorkflowRuns(g);
        setCases(caseRows);
        if (runs.length) {
          const full = await fetchGovernanceRun(runs[0].id);
          setParsedRun(parseGovernanceRunResult(full));
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load command center"));
  }, []);

  const runWorkflow = async (workflowType: string) => {
    try {
      const latestIncident = incidents[0];
      const out = await runGovernanceWorkflow(workflowType, latestIncident?.id);
      setWorkflowRuns((prev) => [out, ...prev].slice(0, 10));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Workflow execution failed");
    }
  };

  const rerunRar = async () => {
    try {
      const latestIncident = incidents[0];
      if (!latestIncident) return;
      const rerun = await runRarIteration(latestIncident.id);
      setIncidents((prev) =>
        prev.map((i) => (i.id === latestIncident.id ? { ...i, confidence: rerun.confidence_after } : i))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "RAR run failed");
    }
  };

  const riskCards = deriveRiskCards(releaseGov, consensus, parsedRun);
  const recommendation = deriveRecommendation(parsedRun, releaseGov);
  const recentDecisions = deriveRecentDecisions(summary, cases);
  const flowSteps = deriveDecisionFlow(parsedRun);
  const liveTrace = parsedRun ? isLiveTrace(parsedRun.run.finished_at) : false;

  const maxRunCount = Math.max(1, ...Object.values(summary?.run_status_counts ?? { empty: 1 }));
  const maxCaseCount = Math.max(1, ...Object.values(summary?.case_status_counts ?? { empty: 1 }));

  return (
    <div className="app dashboard-page">
      <header className="gov-hub-header">
        <p className="gov-hub-eyebrow">Command Center</p>
        <h1 className="gov-hub-title">AI governance for software delivery, cost, and operational risk</h1>
        <p className="gov-hub-lead">
          Real-time decision cockpit synthesizing GitHub, Jira, and FinOps signals into one trustworthy recommendation.
        </p>
      </header>

      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}

      <RiskMetricCard cards={riskCards} />

      {!parsedRun && !recommendation ? (
        <div className="gov-empty-cta">
          <strong>No succeeded governance run yet.</strong>
          <p style={{ margin: "0.35rem 0 0.75rem", color: "var(--muted)" }}>
            Run a governance check in Ask Casantris AI to populate the command center.
          </p>
          <Link to="/app/overview" className="btn btn-primary btn-sm">
            Ask Casantris AI →
          </Link>
        </div>
      ) : null}

      {recommendation ? (
        <div className="gov-command-split">
          <AIRecommendationCard recommendation={recommendation} />
          <RecentDecisionsList items={recentDecisions} />
        </div>
      ) : (
        <RecentDecisionsList items={recentDecisions} />
      )}

      <DecisionFlowTrace steps={flowSteps} live={liveTrace} />

      <details className="card" style={{ marginTop: "1rem" }} open={showAdvanced} onToggle={(e) => setShowAdvanced(e.currentTarget.open)}>
        <summary style={{ cursor: "pointer", fontWeight: 600 }}>Advanced operations</summary>
        <section className="dashboard-section" style={{ marginTop: "1rem" }}>
          <div className="metrics dashboard-kpis">
            <div className="metric">
              <div className="label">Runs (24h)</div>
              <div className="value">{summary?.runs_24h ?? "…"}</div>
            </div>
            <div className="metric">
              <div className="label">Success (24h)</div>
              <div className="value good">{summary?.runs_success_24h ?? "…"}</div>
            </div>
            <div className="metric">
              <div className="label">Open cases</div>
              <div className="value warn">{summary?.cases_open ?? "…"}</div>
            </div>
            <div className="metric">
              <div className="label">Alerts (24h)</div>
              <div className="value bad">{summary?.alerts_24h ?? "…"}</div>
            </div>
            <div className="metric">
              <div className="label">Req/min</div>
              <div className="value">{obs?.requests_per_min ?? "…"}</div>
            </div>
            <div className="metric">
              <div className="label">Consensus</div>
              <div className="value">{consensus ? consensus.avg_consensus_score.toFixed(2) : "…"}</div>
            </div>
          </div>
        </section>

        <div className="card">
          <div className="dashboard-card-toolbar">
            <h2>Cross-agent incidents</h2>
            <div className="actions">
              <button className="btn btn-ghost" type="button" onClick={rerunRar} disabled={!incidents.length}>
                RAR Re-analyze
              </button>
              <button className="btn btn-ghost" type="button" onClick={() => runWorkflow("cost_spike")}>
                Cost spike workflow
              </button>
              <button className="btn btn-ghost" type="button" onClick={() => runWorkflow("security_governance")}>
                Security workflow
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
          {incidents[0] ? (
            <div style={{ marginTop: "1rem" }}>
              <h3 style={{ margin: "0 0 0.5rem", fontSize: "0.95rem" }}>Agent findings (latest incident)</h3>
              <IncidentFindingsPanel incident={incidents[0]} />
            </div>
          ) : null}
        </div>

        <div className="dashboard-grid">
          <div className="card">
            <h2>Run status</h2>
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
            <h2>Case status</h2>
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
            {execSummaries.length ? (
              <ul className="list-plain">
                {execSummaries.map((s) => (
                  <li key={s.id}>
                    <span className="status-chip succeeded">XI {s.xi_score.toFixed(2)}</span> {s.content}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state">No executive summaries yet.</div>
            )}
          </div>
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
                  </tr>
                </thead>
                <tbody>
                  {workflowRuns.map((w) => (
                    <tr key={w.id}>
                      <td>{w.workflow_type}</td>
                      <td>{w.decision ?? "—"}</td>
                      <td>{w.score.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="card">
            <h2>Alerts stream</h2>
            {(summary?.recent_alerts ?? []).length ? (
              <ul className="list-plain">
                {(summary?.recent_alerts ?? []).map((e) => (
                  <li key={e.id}>
                    <span className={`status-chip ${e.severity === "critical" ? "failed" : "running"}`}>{e.severity}</span>{" "}
                    {e.summary}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state">No recent alerts.</div>
            )}
          </div>
        </div>
      </details>
    </div>
  );
}
