import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { exportRunBriefPdf, fetchGovernanceRun } from "../api";
import { GovernanceFlowStepper } from "../components/governance/GovernanceFlowStepper";
import { GuardrailStatusPanel } from "../components/governance/GuardrailStatusPanel";
import { parseGovernanceRunResult } from "../lib/governancePresentation";

export function WorkspaceBriefPage() {
  const [searchParams] = useSearchParams();
  const runId = Number(searchParams.get("run_id") || 0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [parsed, setParsed] = useState<ReturnType<typeof parseGovernanceRunResult>>(null);

  useEffect(() => {
    if (!runId) return;
    setLoading(true);
    fetchGovernanceRun(runId)
      .then((run) => setParsed(parseGovernanceRunResult(run)))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load run"))
      .finally(() => setLoading(false));
  }, [runId]);

  const brief = parsed?.result.governance_brief;
  const markdown = brief?.markdown ?? parsed?.result.explanation ?? "";

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
      <div className="card empty-state">
        <p>Select a governance run to view the executive brief.</p>
        <Link to="/app/runs" className="btn btn-primary btn-sm">
          Open Agentic Governance
        </Link>
      </div>
    );
  }

  return (
    <div className="workspace-page">
      <GovernanceFlowStepper runId={runId} activeStep="brief" />
      {loading ? <div className="empty-state">Loading brief…</div> : null}
      {error ? <div className="alert alert-error">{error}</div> : null}
      {parsed ? (
        <>
          <article className="card">
            <div className="workspace-section-intro">
              <div>
                <p className="gov-hub-eyebrow">Screen 5 — Brief</p>
                <h1 style={{ margin: 0 }}>{brief?.executive_title ?? parsed.result.pm_view?.title ?? "Governance Brief"}</h1>
              </div>
              <div className="gov-recommendation-actions">
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => void handlePdf()}>
                  Export PDF
                </button>
                <Link to={`/app/runs?run_id=${runId}`} className="btn btn-ghost btn-sm">
                  Agent reasoning
                </Link>
              </div>
            </div>
            {brief?.executive_summary ? <p style={{ fontWeight: 600 }}>{brief.executive_summary}</p> : null}
            <div className="pm-summary">
              <ReactMarkdown>{markdown}</ReactMarkdown>
            </div>
          </article>
          <GuardrailStatusPanel
            guardrails={parsed.result.guardrails}
            llmCost={parsed.result.llm_cost}
            llmBudget={parsed.result.llm_budget}
          />
        </>
      ) : null}
    </div>
  );
}
