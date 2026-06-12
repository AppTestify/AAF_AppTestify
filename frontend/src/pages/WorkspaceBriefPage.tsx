import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { exportRunBriefPdf, fetchGovernanceRun } from "../api";
import { BriefJumpNav } from "../components/governance/BriefJumpNav";
import { GovernanceFlowStepper } from "../components/governance/GovernanceFlowStepper";
import { GuardrailStatusPanel } from "../components/governance/GuardrailStatusPanel";
import { WorkspacePageShell } from "../components/layout/WorkspacePageShell";
import { formatRelativeTime, parseGovernanceRunResult } from "../lib/governancePresentation";

const JUMP_TARGETS: Record<string, string> = {
  executive: "brief-executive",
  guardrails: "brief-guardrails",
  reasoning: "brief-reasoning",
  audit: "brief-audit",
  cost: "brief-cost",
};

export function WorkspaceBriefPage() {
  const [searchParams] = useSearchParams();
  const runId = Number(searchParams.get("run_id") || 0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [activeSection, setActiveSection] = useState("executive");

  const [parsed, setParsed] = useState<ReturnType<typeof parseGovernanceRunResult>>(null);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const poll = async () => {
      try {
        const run = await fetchGovernanceRun(runId);
        if (cancelled) return;
        if (run.status === "queued" || run.status === "running") {
          setProcessing(true);
          setLoading(false);
          setParsed(parseGovernanceRunResult(run));
          timer = setTimeout(() => void poll(), 1500);
          return;
        }
        setProcessing(false);
        setLoading(false);
        if (run.status === "failed") {
          setError(run.error_message ?? "Run failed");
          setParsed(null);
          return;
        }
        setParsed(parseGovernanceRunResult(run));
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load run");
          setLoading(false);
          setProcessing(false);
        }
      }
    };

    setLoading(true);
    setError(null);
    setBannerDismissed(false);
    void poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [runId]);

  const brief = parsed?.result.governance_brief;
  const markdown = brief?.markdown ?? parsed?.result.explanation ?? "";

  const scrollToSection = (sectionId: string) => {
    setActiveSection(sectionId);
    const el = document.getElementById(JUMP_TARGETS[sectionId] ?? sectionId);
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const handlePdf = async () => {
    if (!runId) return;
    try {
      const blob = await exportRunBriefPdf(runId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `governance_brief_${runId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF export failed");
    }
  };

  if (!runId) {
    return (
      <WorkspacePageShell variant="governance" eyebrow="Executive Brief" title="Governance narrative" subtitle="Select a run to view the executive brief.">
        <div className="card empty-state">
          <p>Select a governance run to view the executive brief.</p>
          <Link to="/app/runs" className="btn btn-primary btn-sm">
            Open Agentic Governance
          </Link>
        </div>
      </WorkspacePageShell>
    );
  }

  const runStatus = parsed?.run.status;

  return (
    <WorkspacePageShell
      variant="governance"
      eyebrow="Executive Brief"
      title={brief?.executive_title ?? parsed?.result.pm_view?.title ?? "Governance Brief"}
      subtitle="Print-friendly executive narrative with guardrail posture."
      className="brief-page"
    >
      {processing && !bannerDismissed ? (
        <div className="brief-processing-banner" role="status">
          <span>
            <span className="status-pulse-dot" aria-hidden="true" />
            Run #{runId} is still processing — brief will refresh automatically when complete.
          </span>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setBannerDismissed(true)}>
            Dismiss
          </button>
        </div>
      ) : null}

      <GovernanceFlowStepper runId={runId} activeStep="brief" />

      {parsed ? (
        <p className="brief-run-meta">
          Run #{runId} · {runStatus} · {formatRelativeTime(parsed.run.finished_at ?? parsed.run.created_at)}
        </p>
      ) : null}

      {loading ? <div className="empty-state">Loading brief…</div> : null}
      {error ? <div className="alert alert-error">{error}</div> : null}
      {parsed ? (
        <div className="brief-layout brief-layout--jump-nav">
          <BriefJumpNav activeId={activeSection} onSelect={scrollToSection} />
          <article className="card brief-article brief-print-target">
            <div className="workspace-section-intro">
              <div>
                <p className="gov-hub-eyebrow">Screen 5 — Brief</p>
                <h1 id="brief-executive" className="brief-title">
                  {brief?.executive_title ?? parsed.result.pm_view?.title ?? "Governance Brief"}
                </h1>
              </div>
              <div className="gov-recommendation-actions brief-print-hide">
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => void handlePdf()}>
                  Export PDF
                </button>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => window.print()}>
                  Print
                </button>
                <Link to={`/app/runs?run_id=${runId}`} className="btn btn-ghost btn-sm">
                  Agent reasoning
                </Link>
              </div>
            </div>
            {brief?.executive_summary ? (
              <p id="brief-executive-summary" className="brief-summary">
                {brief.executive_summary}
              </p>
            ) : null}
            <div className="pm-summary brief-body">
              <ReactMarkdown>{markdown}</ReactMarkdown>
            </div>
            <section id="brief-reasoning" className="brief-section-anchor">
              <h3>Agent reasoning</h3>
              <p className="workspace-meta">
                Full multi-agent opinions and consensus metrics live on the run detail page.
              </p>
              <Link to={`/app/runs?run_id=${runId}`} className="btn btn-ghost btn-sm">
                Open run #{runId} →
              </Link>
            </section>
            <section id="brief-audit" className="brief-section-anchor">
              <h3>Audit trail</h3>
              <p className="workspace-meta">
                Evidence snapshots and case decisions linked to this run are available in Evidence Hub and Cases.
              </p>
              <div className="actions">
                <Link to={`/app/evidence?run_id=${runId}`} className="btn btn-ghost btn-sm">
                  Evidence
                </Link>
                <Link to={`/app/cases`} className="btn btn-ghost btn-sm">
                  Cases
                </Link>
              </div>
            </section>
          </article>
          <aside className="brief-guardrail-panel brief-print-hide">
            <div id="brief-guardrails">
              <GuardrailStatusPanel
                guardrails={parsed.result.guardrails}
                llmCost={parsed.result.llm_cost}
                llmBudget={parsed.result.llm_budget}
                compact
              />
            </div>
            <div id="brief-cost" className="brief-cost-panel">
              <h3>LLM cost</h3>
              <p className="workspace-meta">
                {parsed.result.llm_cost?.totals?.cost_usd != null
                  ? `Total spend: $${parsed.result.llm_cost.totals.cost_usd.toFixed(4)}`
                  : "No LLM cost data for this run."}
              </p>
            </div>
          </aside>
        </div>
      ) : processing ? (
        <div className="card empty-state">
          <p>Brief content will appear when run #{runId} completes.</p>
        </div>
      ) : null}
    </WorkspacePageShell>
  );
}
