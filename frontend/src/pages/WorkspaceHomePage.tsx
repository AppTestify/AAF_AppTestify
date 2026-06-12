import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchCases,
  fetchConsensusSummary,
  fetchExecutiveSummaries,
  fetchGovernanceRun,
  fetchGovernanceRuns,
  fetchWorkflowRuns,
  fetchIntelligenceIncidents,
  fetchObservabilitySummary,
  fetchReleaseGovernance,
  fetchRunsTimeseries,
  runGovernanceWorkflow,
  runRarIteration,
  type ConsensusSummary,
  type ExecutiveSummary,
  type IntelligenceIncident,
  type ObservabilitySummary,
  type ReleaseGovernance,
  type RunsTimeseries,
  type UserPublic,
  type GovernanceCase,
  type WorkflowRun,
} from "../api";
import { CaseStatusBar } from "../components/charts/CaseStatusBar";
import { ConnectorHealthDonut } from "../components/charts/ConnectorHealthDonut";
import { LlmCostBar } from "../components/charts/LlmCostBar";
import { RunsTrendLine } from "../components/charts/RunsTrendLine";
import { RunStatusDonut } from "../components/charts/RunStatusDonut";
import { SloBurnChart } from "../components/charts/SloBurnChart";
import { AIRecommendationCard } from "../components/governance/AIRecommendationCard";
import { DecisionFlowTrace } from "../components/governance/DecisionFlowTrace";
import { ConnectorHealthCards } from "../components/governance/ConnectorHealthCards";
import { RecentDecisionsList } from "../components/governance/RecentDecisionsList";
import { RecentRunsList } from "../components/governance/RecentRunsList";
import { RiskMetricCard } from "../components/governance/RiskMetricCard";
import { IncidentFindingsPanel } from "../components/IncidentFindingsPanel";
import { WorkspacePageShell } from "../components/layout/WorkspacePageShell";
import { EmptyState } from "../components/ui/EmptyState";
import { KpiStrip } from "../components/ui/KpiStrip";
import { useDashboardSummary } from "../hooks/useDashboardSummary";
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
  const { summary, loading: summaryLoading, error: summaryError } = useDashboardSummary();
  const [timeseries, setTimeseries] = useState<RunsTimeseries | null>(null);
  const [obs, setObs] = useState<ObservabilitySummary | null>(null);
  const [consensus, setConsensus] = useState<ConsensusSummary | null>(null);
  const [incidents, setIncidents] = useState<IntelligenceIncident[]>([]);
  const [execSummaries, setExecSummaries] = useState<ExecutiveSummary[]>([]);
  const [releaseGov, setReleaseGov] = useState<ReleaseGovernance | null>(null);
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRun[]>([]);
  const [parsedRun, setParsedRun] = useState<ParsedRunContext | null>(null);
  const [cases, setCases] = useState<GovernanceCase[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [opsLoading, setOpsLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchRunsTimeseries(7),
      fetchObservabilitySummary(),
      fetchConsensusSummary(),
      fetchIntelligenceIncidents(6),
      fetchExecutiveSummaries(3),
      fetchReleaseGovernance(),
      fetchWorkflowRuns(),
      fetchCases(20),
      fetchGovernanceRuns({ status: "succeeded", limit: 1 }),
    ])
      .then(async ([ts, b, c, d, e, f, g, casePage, runPage]) => {
        setTimeseries(ts);
        setObs(b);
        setConsensus(c);
        setIncidents(d);
        setExecSummaries(e);
        setReleaseGov(f);
        setWorkflowRuns(g);
        setCases(Array.isArray(casePage) ? casePage : casePage.items);
        const runs = Array.isArray(runPage) ? runPage : runPage.items;
        if (runs.length) {
          const full = await fetchGovernanceRun(runs[0].id);
          setParsedRun(parseGovernanceRunResult(full));
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load command center"))
      .finally(() => setOpsLoading(false));
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
  const flowSteps = deriveDecisionFlow(parsedRun, parsedRun?.run.status);
  const liveTrace = parsedRun ? isLiveTrace(parsedRun.run.status, parsedRun.run.finished_at) : false;
  const displayError = error ?? summaryError;
  const chartsLoading = summaryLoading || opsLoading;

  return (
    <WorkspacePageShell
      variant="governance"
      dashboard
      eyebrow="Command Center"
      title="AI governance for software delivery, cost, and operational risk"
      subtitle="Real-time decision cockpit synthesizing GitHub, Jira, and FinOps signals into one trustworthy recommendation."
    >
      {displayError ? (
        <div className="alert alert-error" role="alert">
          {displayError}
        </div>
      ) : null}

      <KpiStrip
        loading={chartsLoading}
        items={[
          { label: "Runs (24h)", value: summary?.runs_24h ?? "…" },
          { label: "Success (24h)", value: summary?.runs_success_24h ?? "…", tone: "good" },
          { label: "Open cases", value: summary?.cases_open ?? "…", tone: "warn" },
          { label: "Alerts (24h)", value: summary?.alerts_24h ?? "…", tone: "bad" },
          { label: "Req/min", value: obs?.requests_per_min ?? "…" },
          {
            label: "Consensus",
            value: consensus ? consensus.avg_consensus_score.toFixed(2) : "…",
          },
        ]}
      />

      <ConnectorHealthCards connectors={summary?.connector_health} />

      <RecentRunsList runs={summary?.recent_runs} />

      <div className="dashboard-charts-row">
        <RunStatusDonut counts={summary?.run_status_counts} />
        <CaseStatusBar counts={summary?.case_status_counts} />
        <ConnectorHealthDonut connectors={summary?.connector_health} />
      </div>

      <div className="dashboard-charts-row">
        <RunsTrendLine data={timeseries} loading={chartsLoading} />
        <SloBurnChart slo={obs?.slo_burn_rate} loading={chartsLoading} />
        <LlmCostBar invocation={obs?.llm_invocation} loading={chartsLoading} />
      </div>

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
            <EmptyState>No executive summaries yet.</EmptyState>
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
            <EmptyState>No recent alerts.</EmptyState>
          )}
        </div>
      </div>
    </WorkspacePageShell>
  );
}
