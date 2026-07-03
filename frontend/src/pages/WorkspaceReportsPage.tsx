import { useEffect, useMemo, useState } from "react";
import {
  emailReport,
  fetchAuditEvents,
  fetchAuditExport,
  fetchConsensusSummary,
  fetchExecutivePortfolioReport,
  fetchPortfolioExecutiveExport,
  fetchGovernanceRuns,
  fetchIntelligenceIncidents,
  fetchReleaseGovernance,
  fetchRunSummaryReport,
  fetchWorkflowRuns,
  type AuditEvent,
  type ConsensusSummary,
  type ExecutivePortfolioReport,
  type GovernanceRunV1,
  type IntelligenceIncident,
  type ReleaseGovernance,
  type WorkflowRun,
} from "../api";
import { CountBarChart } from "../components/charts/CountBarChart";
import { CountDonutChart } from "../components/charts/CountDonutChart";
import { IncidentFindingsPanel } from "../components/IncidentFindingsPanel";
import { WorkspacePageShell } from "../components/layout/WorkspacePageShell";
import { DataTable } from "../components/ui/DataTable";
import { KpiStrip } from "../components/ui/KpiStrip";
import { SectionCard } from "../components/ui/SectionCard";
import { SegmentedTabs } from "../components/ui/SegmentedTabs";

type WorkspaceReportsPageProps = {
  };

type ReportTab = "overview" | "governance" | "incidents" | "audit" | "exports";
type AuditDateRange = "7d" | "30d" | "90d";

const REPORT_TABS: { id: ReportTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "governance", label: "Governance" },
  { id: "incidents", label: "Incidents" },
  { id: "audit", label: "Audit" },
  { id: "exports", label: "Exports" },
];

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function auditRangeDays(range: AuditDateRange): number {
  if (range === "7d") return 7;
  if (range === "30d") return 30;
  return 90;
}

export function WorkspaceReportsPage({}: WorkspaceReportsPageProps) {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<ReportTab>("overview");
  const [runs, setRuns] = useState<GovernanceRunV1[]>([]);
  const [incidents, setIncidents] = useState<IntelligenceIncident[]>([]);
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRun[]>([]);
  const [auditRows, setAuditRows] = useState<AuditEvent[]>([]);
  const [consensus, setConsensus] = useState<ConsensusSummary | null>(null);
  const [releaseGov, setReleaseGov] = useState<ReleaseGovernance | null>(null);
  const [portfolioReport, setPortfolioReport] = useState<ExecutivePortfolioReport | null>(null);
  const [output, setOutput] = useState<string>("");
  const [toast, setToast] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [runStatusFilter, setRunStatusFilter] = useState<string>("");
  const [auditAreaFilter, setAuditAreaFilter] = useState<string>("");
  const [auditDateRange, setAuditDateRange] = useState<AuditDateRange>("30d");
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [emailReportType, setEmailReportType] = useState<"runs_summary" | "audit_events" | "portfolio_executive">("runs_summary");
  const [emailFormat, setEmailFormat] = useState<"xlsx" | "pdf">("xlsx");
  const [emailRecipients, setEmailRecipients] = useState("");
  const [emailSending, setEmailSending] = useState(false);

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
      fetchAuditEvents({ limit: 500 }),
      fetchConsensusSummary(),
      fetchReleaseGovernance(),
      fetchExecutivePortfolioReport(),
    ])
      .then(([runPage, i, w, auditPage, c, g, p]) => {
        setRuns(runPage.items);
        setIncidents(i);
        setWorkflowRuns(w);
        setAuditRows(auditPage.items);
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

  const filteredAuditRows = useMemo(() => {
    const cutoff = Date.now() - auditRangeDays(auditDateRange) * 24 * 60 * 60 * 1000;
    return auditRows.filter((row) => new Date(row.created_at).getTime() >= cutoff);
  }, [auditRows, auditDateRange]);

  const auditByAreaCounts = useMemo(() => {
    const out: Record<string, number> = {};
    for (const row of filteredAuditRows) out[row.area] = (out[row.area] ?? 0) + 1;
    return out;
  }, [filteredAuditRows]);

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

  const exportRunsXlsx = async () => {
    try {
      setError("");
      const blob = (await fetchRunSummaryReport("xlsx", 200, runStatusFilter || undefined)) as Blob;
      downloadBlob(blob, "governance_run_summary.xlsx");
      notify("Run summary Excel downloaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Excel export failed");
    }
  };

  const exportRunsPdf = async () => {
    try {
      setError("");
      const blob = (await fetchRunSummaryReport("pdf", 200, runStatusFilter || undefined)) as Blob;
      downloadBlob(blob, "governance_run_summary.pdf");
      notify("Run summary PDF downloaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF export failed");
    }
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

  const sendReportEmail = async () => {
    const recipients = emailRecipients
      .split(/[\n,]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (!recipients.length) {
      setError("Enter at least one recipient email");
      return;
    }
    try {
      setEmailSending(true);
      setError("");
      const result = await emailReport({
        report_type: emailReportType,
        format: emailFormat,
        recipients,
        status: emailReportType === "runs_summary" ? runStatusFilter || undefined : undefined,
        area: emailReportType === "audit_events" ? auditAreaFilter || undefined : undefined,
        limit: 200,
      });
      notify(`Report emailed to ${result.sent_to.join(", ")}`);
      setEmailModalOpen(false);
      setEmailRecipients("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Email report failed");
    } finally {
      setEmailSending(false);
    }
  };

  const exportAuditXlsx = async () => {
    try {
      setError("");
      const blob = (await fetchAuditExport("xlsx", auditAreaFilter || undefined)) as Blob;
      downloadBlob(blob, "audit_events.xlsx");
      notify("Audit Excel downloaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Audit Excel export failed");
    }
  };

  const exportAuditPdf = async () => {
    try {
      setError("");
      const blob = (await fetchAuditExport("pdf", auditAreaFilter || undefined)) as Blob;
      downloadBlob(blob, "audit_events.pdf");
      notify("Audit PDF downloaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Audit PDF export failed");
    }
  };

  const exportPortfolioXlsx = async () => {
    try {
      setError("");
      const blob = (await fetchPortfolioExecutiveExport("xlsx")) as Blob;
      downloadBlob(blob, "portfolio_executive.xlsx");
      notify("Portfolio executive Excel downloaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Portfolio Excel export failed");
    }
  };

  const exportPortfolioPdf = async () => {
    try {
      setError("");
      const blob = (await fetchPortfolioExecutiveExport("pdf")) as Blob;
      downloadBlob(blob, "portfolio_executive.pdf");
      notify("Portfolio executive PDF downloaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Portfolio PDF export failed");
    }
  };

  return (
    <WorkspacePageShell
      variant="operational"
      title="Reports"
      subtitle="Comprehensive operational, intelligence, workflow, and audit reporting center"
    >
      <SegmentedTabs
        tabs={REPORT_TABS}
        activeId={activeTab}
        onChange={(id) => setActiveTab(id as ReportTab)}
        aria-label="Reports sections"
      />

      {toast ? <div className="alert alert-success">{toast}</div> : null}
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      {loading ? <div className="card">Loading reports…</div> : null}

      {!loading && activeTab === "overview" ? (
        <>
          <KpiStrip
            items={[
              { label: "Total runs", value: runs.length },
              { label: "Incidents", value: incidents.length, tone: "warn" },
              { label: "Workflow runs", value: workflowRuns.length },
              { label: "Audit events", value: auditRows.length },
              { label: "Avg consensus", value: consensus ? consensus.avg_consensus_score.toFixed(2) : "—" },
              { label: "Release decision", value: releaseGov?.decision ?? "—" },
              { label: "Portfolio projects", value: portfolioReport?.projects_total ?? "—" },
            ]}
          />
          <SectionCard
            title="Executive portfolio report"
            description="Cross-project release readiness and decision posture for leadership governance."
          >
            <KpiStrip
              items={[
                { label: "Releases total", value: portfolioReport?.releases_total ?? 0 },
                { label: "Approved", value: portfolioReport?.releases_approved ?? 0, tone: "good" },
                { label: "Blocked", value: portfolioReport?.releases_blocked ?? 0, tone: "warn" },
                { label: "High risk", value: portfolioReport?.high_risk_open ?? 0, tone: "warn" },
                {
                  label: "Avg confidence",
                  value: `${((portfolioReport?.avg_confidence ?? 0) * 100).toFixed(1)}%`,
                },
              ]}
            />
          </SectionCard>
          <SectionCard
            title="Operational distribution"
            description="Visual breakdown of run status, incident severity, and workflow types."
          >
            <div className="dashboard-charts-row">
              <CountDonutChart title="Run status" counts={runStatusCounts} />
              <CountBarChart title="Incident severity" counts={severityCounts} />
              <CountBarChart title="Workflow types" counts={workflowTypeCounts} />
            </div>
          </SectionCard>
        </>
      ) : null}

      {!loading && activeTab === "governance" ? (
        <>
          <KpiStrip
            items={[
              { label: "Incidents tracked", value: consensus?.incidents_total ?? 0 },
              {
                label: "Avg consensus",
                value: consensus ? consensus.avg_consensus_score.toFixed(2) : "—",
                tone: "good",
              },
              {
                label: "Avg confidence",
                value: consensus ? consensus.avg_confidence.toFixed(2) : "—",
              },
              {
                label: "Conflict rate",
                value: consensus ? `${(consensus.conflict_rate * 100).toFixed(1)}%` : "—",
                tone: consensus && consensus.conflict_rate > 0.2 ? "warn" : "default",
              },
              { label: "High risk open", value: consensus?.high_risk_open ?? 0, tone: "warn" },
              { label: "Release decision", value: releaseGov?.decision ?? "—" },
            ]}
          />
          <SectionCard
            title="Governance run outcomes"
            description="Run-level status, timing, and orchestration results across the workspace."
          >
            <DataTable
              columns={[
                { key: "id", header: "Run", render: (row) => `#${row.id}` },
                { key: "status", header: "Status", render: (row) => row.status },
                {
                  key: "prompt",
                  header: "Prompt",
                  render: (row) =>
                    row.prompt.length > 72 ? `${row.prompt.slice(0, 72)}…` : row.prompt,
                },
                {
                  key: "created",
                  header: "Created",
                  render: (row) => new Date(row.created_at).toLocaleString(),
                },
                {
                  key: "finished",
                  header: "Finished",
                  render: (row) =>
                    row.finished_at ? new Date(row.finished_at).toLocaleString() : "—",
                },
              ]}
              rows={runs.slice(0, 50)}
              rowKey={(row) => String(row.id)}
              emptyMessage="No governance runs recorded."
            />
          </SectionCard>
        </>
      ) : null}

      {!loading && activeTab === "incidents" ? (
        <>
          <SectionCard
            title="Incident severity"
            description="Distribution of correlated intelligence incidents by severity band."
          >
            <CountDonutChart title="Severity breakdown" counts={severityCounts} />
          </SectionCard>
          <SectionCard
            title="Incident intelligence report"
            description="Top correlated incidents with confidence and consensus indicators."
          >
            <DataTable
              columns={[
                { key: "title", header: "Incident", render: (row) => row.title },
                { key: "severity", header: "Severity", render: (row) => row.severity },
                {
                  key: "consensus",
                  header: "Consensus",
                  render: (row) => row.consensus_score.toFixed(2),
                },
                {
                  key: "confidence",
                  header: "Confidence",
                  render: (row) => row.confidence.toFixed(2),
                },
                { key: "status", header: "Status", render: (row) => row.status },
              ]}
              rows={incidents.slice(0, 25)}
              rowKey={(row) => String(row.id)}
              emptyMessage="No incidents recorded."
            />
            {incidents.slice(0, 5).map((incident) => (
              <details key={`findings-${incident.id}`} className="accordion">
                <summary>
                  Agent findings — {incident.title.slice(0, 72)}
                  {incident.title.length > 72 ? "…" : ""}
                </summary>
                <IncidentFindingsPanel incident={incident} />
              </details>
            ))}
          </SectionCard>
        </>
      ) : null}

      {!loading && activeTab === "audit" ? (
        <>
          <SegmentedTabs
            tabs={[
              { id: "7d", label: "7d" },
              { id: "30d", label: "30d" },
              { id: "90d", label: "90d" },
            ]}
            activeId={auditDateRange}
            onChange={(id) => setAuditDateRange(id as AuditDateRange)}
            aria-label="Audit date range"
          />
          <SectionCard
            title="Audit activity by area"
            description="Event volume grouped by audit area for the selected date window."
          >
            <KpiStrip
              items={[
                { label: "Events in range", value: filteredAuditRows.length },
                { label: "Distinct areas", value: Object.keys(auditByAreaCounts).length },
                { label: "Date window", value: auditDateRange },
              ]}
            />
            <CountBarChart title="Events by area" counts={auditByAreaCounts} horizontal />
          </SectionCard>
          <SectionCard
            title="Audit event log"
            description={`Client-side filter on loaded events for the last ${auditDateRange}.`}
          >
            <DataTable
              columns={[
                { key: "area", header: "Area", render: (row) => row.area },
                { key: "action", header: "Action", render: (row) => row.action },
                { key: "severity", header: "Severity", render: (row) => row.severity },
                { key: "summary", header: "Summary", render: (row) => row.summary },
                {
                  key: "created",
                  header: "Created",
                  render: (row) => new Date(row.created_at).toLocaleString(),
                },
              ]}
              rows={filteredAuditRows.slice(0, 100)}
              rowKey={(row) => String(row.id)}
              emptyMessage="No audit events in the selected date range."
            />
          </SectionCard>
        </>
      ) : null}

      {!loading && activeTab === "exports" ? (
        <>
          <div className="card-group">
            <SectionCard
              title="Run summary export"
              description="Filter run-level outcomes, inspect JSON, or download governance summary in CSV, Excel, or PDF."
            >
              <div className="workspace-toolbar">
                <div className="form-row">
                  <label htmlFor="report-run-status">Run status</label>
                  <select
                    id="report-run-status"
                    value={runStatusFilter}
                    onChange={(e) => setRunStatusFilter(e.target.value)}
                  >
                    <option value="">All</option>
                    <option value="queued">Queued</option>
                    <option value="running">Running</option>
                    <option value="succeeded">Succeeded</option>
                    <option value="failed">Failed</option>
                  </select>
                </div>
              </div>
              <div className="actions">
                <button className="btn btn-primary" type="button" onClick={exportRunsCsv}>
                  Download CSV
                </button>
                <button className="btn btn-primary" type="button" onClick={exportRunsXlsx}>
                  Download Excel
                </button>
                <button className="btn btn-primary" type="button" onClick={exportRunsPdf}>
                  Download PDF
                </button>
                <button className="btn btn-secondary" type="button" onClick={exportRunsJson}>
                  View JSON
                </button>
              </div>
            </SectionCard>
            <SectionCard
              title="Audit export"
              description="Query audit events by area and extract JSON, CSV, Excel, or PDF for compliance trails."
            >
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
                <button className="btn btn-primary" type="button" onClick={exportAuditCsv}>
                  Download CSV
                </button>
                <button className="btn btn-primary" type="button" onClick={exportAuditXlsx}>
                  Download Excel
                </button>
                <button className="btn btn-primary" type="button" onClick={exportAuditPdf}>
                  Download PDF
                </button>
                <button className="btn btn-secondary" type="button" onClick={exportAuditJson}>
                  View JSON
                </button>
              </div>
            </SectionCard>
            <SectionCard
              title="Portfolio executive export"
              description="Leadership-ready portfolio posture in Excel or PDF."
            >
              <div className="actions">
                <button className="btn btn-primary" type="button" onClick={exportPortfolioXlsx}>
                  Download Excel
                </button>
                <button className="btn btn-primary" type="button" onClick={exportPortfolioPdf}>
                  Download PDF
                </button>
              </div>
            </SectionCard>
            <SectionCard
              title="Email report"
              description="Send an Excel or PDF attachment to recipients via tenant or platform SMTP."
            >
              <div className="actions">
                <button className="btn btn-primary" type="button" onClick={() => setEmailModalOpen(true)}>
                  Email this report…
                </button>
              </div>
            </SectionCard>
          </div>
          {emailModalOpen ? (
            <div className="modal-backdrop" role="presentation" onClick={() => setEmailModalOpen(false)}>
              <div className="modal card" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
                <h3>Email report</h3>
                <div className="form-row">
                  <label htmlFor="email-report-type">Report</label>
                  <select
                    id="email-report-type"
                    value={emailReportType}
                    onChange={(e) => setEmailReportType(e.target.value as typeof emailReportType)}
                  >
                    <option value="runs_summary">Governance run summary</option>
                    <option value="audit_events">Audit events</option>
                    <option value="portfolio_executive">Portfolio executive</option>
                  </select>
                </div>
                <div className="form-row">
                  <label htmlFor="email-report-format">Format</label>
                  <select
                    id="email-report-format"
                    value={emailFormat}
                    onChange={(e) => setEmailFormat(e.target.value as typeof emailFormat)}
                  >
                    <option value="xlsx">Excel (.xlsx)</option>
                    <option value="pdf">PDF</option>
                  </select>
                </div>
                <div className="form-row">
                  <label htmlFor="email-recipients">Recipients</label>
                  <textarea
                    id="email-recipients"
                    rows={3}
                    value={emailRecipients}
                    onChange={(e) => setEmailRecipients(e.target.value)}
                    placeholder="ops@example.com, compliance@example.com"
                  />
                </div>
                <div className="actions">
                  <button className="btn btn-ghost" type="button" onClick={() => setEmailModalOpen(false)}>
                    Cancel
                  </button>
                  <button className="btn btn-primary" type="button" onClick={() => void sendReportEmail()} disabled={emailSending}>
                    {emailSending ? "Sending…" : "Send email"}
                  </button>
                </div>
              </div>
            </div>
          ) : null}
          {output ? (
            <SectionCard
              title="Export preview"
              description="Rendered output for quick validation before sharing."
            >
              <pre className="json-preview">{output}</pre>
            </SectionCard>
          ) : null}
        </>
      ) : null}
    </WorkspacePageShell>
  );
}
