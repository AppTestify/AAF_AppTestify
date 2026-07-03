import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  createGovernanceRun,
  createGovernanceRunShareLink,
  fetchGovernanceRun,
  fetchGovernanceRuns,
  streamGovernanceRun,
  fetchPortfolioProjects,
  exportRunBriefPdf,
  fetchSingleRunExport,
  type GovernanceRunV1,
  type PortfolioProject,
} from "../api";
import { AgentReasoningGrid } from "../components/governance/AgentReasoningGrid";
import { ConsensusDecisionPanel } from "../components/governance/ConsensusDecisionPanel";
import { GovernanceFlowStepper } from "../components/governance/GovernanceFlowStepper";
import { GuardrailStatusPanel } from "../components/governance/GuardrailStatusPanel";
import { RunsListPanel } from "../components/governance/RunsListPanel";
import { WorkspacePageShell } from "../components/layout/WorkspacePageShell";
import { DeepLinkCopyBar } from "../components/ui/DeepLinkCopyBar";
import { KpiStrip } from "../components/ui/KpiStrip";
import { PaginationBar } from "../components/ui/PaginationBar";
import { EmptyState } from "../components/ui/EmptyState";
import { formatRelativeTime } from "../lib/governancePresentation";
import { deriveAgentGrid, parseGovernanceRunResult } from "../lib/governancePresentation";

type WorkspaceRunsPageProps = {
  tenantSlug?: string | null;
};

export function WorkspaceRunsPage({ tenantSlug }: WorkspaceRunsPageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const runIdFromUrl = searchParams.get("run_id") ?? "";
  const queryFromUrl = searchParams.get("query") ?? "";
  const listProjectFilter = searchParams.get("portfolio_project_id") ?? "";
  const setListProjectFilter = (v: string) => {
    const next = new URLSearchParams(searchParams);
    if (v) next.set("portfolio_project_id", v);
    else next.delete("portfolio_project_id");
    next.delete("page");
    setSearchParams(next, { replace: true });
  };

  const syncRunIdToUrl = (runId: number | null) => {
    const next = new URLSearchParams(searchParams);
    if (runId != null) next.set("run_id", String(runId));
    else next.delete("run_id");
    setSearchParams(next, { replace: true });
  };

  const [runs, setRuns] = useState<GovernanceRunV1[]>([]);
  const [runsTotal, setRunsTotal] = useState(0);
  const [projects, setProjects] = useState<PortfolioProject[]>([]);
  const [prompt, setPrompt] = useState("");
  const [promptId, setPromptId] = useState("");
  const [createProjectId, setCreateProjectId] = useState<string>("");
  const [selectedRun, setSelectedRun] = useState<GovernanceRunV1 | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [query, setQuery] = useState<string>("");
  const [isAgentDrawerOpen, setIsAgentDrawerOpen] = useState(false);
  const pageFromUrl = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const pageSizeFromUrl = Math.max(1, Number(searchParams.get("page_size") ?? "50") || 50);
  const offset = (pageFromUrl - 1) * pageSizeFromUrl;

  const syncPaginationToUrl = (page: number, size: number) => {
    const next = new URLSearchParams(searchParams);
    if (page <= 1) next.delete("page");
    else next.set("page", String(page));
    if (size === 50) next.delete("page_size");
    else next.set("page_size", String(size));
    setSearchParams(next, { replace: true });
  };

  const setPage = (page: number) => syncPaginationToUrl(page, pageSizeFromUrl);
  const setPageSize = (size: number) => syncPaginationToUrl(1, size);
  const [toast, setToast] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const projectById = useMemo(() => {
    const m = new Map<number, PortfolioProject>();
    for (const p of projects) m.set(p.id, p);
    return m;
  }, [projects]);

  const activeRunIds = useMemo(
    () => runs.filter((r) => r.status === "queued" || r.status === "running").map((r) => r.id),
    [runs]
  );
  const runStats = useMemo(() => {
    const queued = runs.filter((r) => r.status === "queued").length;
    const running = runs.filter((r) => r.status === "running").length;
    const succeeded = runs.filter((r) => r.status === "succeeded").length;
    const failed = runs.filter((r) => r.status === "failed").length;
    return { queued, running, succeeded, failed };
  }, [runs]);

  useEffect(() => {
    if (queryFromUrl) setQuery(queryFromUrl);
  }, [queryFromUrl]);

  useEffect(() => {
    fetchPortfolioProjects()
      .then(setProjects)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load portfolio projects"));
  }, []);

  useEffect(() => {
    const id = Number(runIdFromUrl);
    if (!runIdFromUrl.trim() || !Number.isFinite(id)) return;
    fetchGovernanceRun(id)
      .then(setSelectedRun)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load run from link"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runIdFromUrl]);

  const loadRuns = async (): Promise<GovernanceRunV1[]> => {
    try {
      setListLoading(true);
      const page = await fetchGovernanceRuns({
        limit: pageSizeFromUrl,
        offset,
        status: statusFilter === "all" ? undefined : statusFilter,
        query: query || undefined,
        portfolio_project_id: listProjectFilter ? Number(listProjectFilter) : undefined,
      });
      setRuns(page.items);
      setRunsTotal(page.total);
      if (selectedRun) {
        const next = page.items.find((r) => r.id === selectedRun.id);
        if (next) setSelectedRun(next);
      }
      return page.items;
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    loadRuns()
      .then(async (list) => {
        if (!runIdFromUrl && !selectedRun) {
          const latest = list.find((r) => r.status === "succeeded");
          if (latest) {
            const full = await fetchGovernanceRun(latest.id);
            setSelectedRun(full);
            syncRunIdToUrl(latest.id);
          }
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load runs"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset, statusFilter, query, listProjectFilter, pageSizeFromUrl]);

  const parsedSelected = useMemo(
    () => (selectedRun?.status === "succeeded" ? parseGovernanceRunResult(selectedRun) : null),
    [selectedRun]
  );
  const agentGrid = parsedSelected
    ? deriveAgentGrid(parsedSelected.result.agent_opinions ?? [], parsedSelected.framing)
    : [];

  useEffect(() => {
    if (activeRunIds.length === 0) return;
    const closers: (() => void)[] = [];
    let pollFallback: ReturnType<typeof setInterval> | null = null;

    const startPollingFallback = () => {
      if (pollFallback) return;
      pollFallback = setInterval(() => {
        loadRuns().catch(() => undefined);
      }, 1200);
    };

    for (const id of activeRunIds) {
      const close = streamGovernanceRun(id, {
        onStatus: () => {
          loadRuns().catch(() => undefined);
        },
        onResultReady: () => {
          fetchGovernanceRun(id)
            .then((run) => {
              setSelectedRun((prev) => (prev?.id === id ? run : prev));
            })
            .catch(() => undefined);
          loadRuns().catch(() => undefined);
        },
        onError: startPollingFallback,
      });
      closers.push(close);
    }

    return () => {
      closers.forEach((close) => close());
      if (pollFallback) clearInterval(pollFallback);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeRunIds.join(",")]);

  const handleCreate = async () => {
    if (!prompt.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const created = await createGovernanceRun({
          prompt: prompt.trim(),
          prompt_id: promptId.trim() || null,
          portfolio_project_id: createProjectId ? Number(createProjectId) : null,
        },
        tenantSlug
      );
      setPrompt("");
      setPromptId("");
      setCreateProjectId("");
      setSelectedRun(created);
      syncRunIdToUrl(created.id);
      setToast(`Run #${created.id} queued`);
      setTimeout(() => setToast(""), 2000);
      await loadRuns();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create run");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectRun = async (runId: number) => {
    syncRunIdToUrl(runId);
    try {
      const row = await fetchGovernanceRun(runId);
      setSelectedRun(row);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load run");
    }
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const selectedRunPath = selectedRun ? `/app/runs?run_id=${selectedRun.id}` : "";

  const copySignedShareLink = async () => {
    if (!selectedRun || selectedRun.status !== "succeeded") return;
    try {
      setError(null);
      const { url } = await createGovernanceRunShareLink(selectedRun.id);
      await navigator.clipboard.writeText(url);
      setToast("Signed public share URL copied (time-limited, no login)");
      setTimeout(() => setToast(""), 2800);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create share link");
    }
  };

  const exportSelectedRunJson = async () => {
    if (!selectedRun) return;
    try {
      setError(null);
      const data = await fetchSingleRunExport(selectedRun.id, "json");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      downloadBlob(blob, `governance_run_${selectedRun.id}.json`);
      setToast("Executive export downloaded");
      setTimeout(() => setToast(""), 2200);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  };

  const exportSelectedRunCsv = async () => {
    if (!selectedRun) return;
    try {
      setError(null);
      const blob = (await fetchSingleRunExport(selectedRun.id, "csv")) as Blob;
      downloadBlob(blob, `governance_run_${selectedRun.id}.csv`);
      setToast("CSV export downloaded");
      setTimeout(() => setToast(""), 2200);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  };

  const exportSelectedRunPdf = async () => {
    if (!selectedRun) return;
    try {
      setError(null);
      const blob = await exportRunBriefPdf(selectedRun.id);
      downloadBlob(blob, `governance_run_${selectedRun.id}.pdf`);
      setToast("Export Brief PDF downloaded");
      setTimeout(() => setToast(""), 2200);
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF export failed");
    }
  };

  return (
    <WorkspacePageShell
      variant="governance"
      eyebrow="Agentic Governance"
      title="How Casantris reasons about this decision"
      subtitle="Specialist agents evaluate domains independently while the orchestrator synthesizes the final recommendation."
    >
      {toast ? <div className="alert alert-success">{toast}</div> : null}
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      {parsedSelected ? (
        <>

          <GovernanceFlowStepper
            runId={parsedSelected.run.id}
            activeStep="runs"
            pipelinePhase={parsedSelected.result.pipeline_phase}
          />
          <ConsensusDecisionPanel
            result={parsedSelected.result}
            framing={parsedSelected.framing}
            runId={parsedSelected.run.id}
            canExecute={parsedSelected.run.status === "succeeded"}
          />
          <GuardrailStatusPanel
            guardrails={parsedSelected.result.guardrails}
            llmCost={parsedSelected.result.llm_cost}
            llmBudget={parsedSelected.result.llm_budget}
          />
        </>
      ) : null}

      <KpiStrip
        items={[
          { label: "Visible runs", value: runs.length },
          { label: "Queued", value: runStats.queued },
          { label: "Running", value: runStats.running, tone: "warn" },
          { label: "Succeeded", value: runStats.succeeded, tone: "good" },
          { label: "Failed", value: runStats.failed, tone: "bad" },
        ]}
      />
      <div className="master-detail-layout">
      <div className="master-detail-list">
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Create run (advanced)</h2>
            <p>
              Prefer the guided prompt on{" "}
              <Link to="/app/overview" className="btn btn-ghost btn-sm">
                Ask Casantris AI
              </Link>{" "}
              — use this form for async queue runs with portfolio linkage.
            </p>
          </div>
          <div className="workspace-meta">Inputs are tenant-scoped</div>
        </div>
        <div className="form-row">
          <label htmlFor="run-prompt" className="field-label-required">Prompt</label>
          <textarea id="run-prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        </div>
        <div className="form-row">
          <label htmlFor="run-prompt-id">Prompt ID (optional)</label>
          <input id="run-prompt-id" value={promptId} onChange={(e) => setPromptId(e.target.value)} />
        </div>
        <div className="form-row">
          <label htmlFor="run-portfolio-project">Portfolio project (optional)</label>
          <select
            id="run-portfolio-project"
            value={createProjectId}
            onChange={(e) => setCreateProjectId(e.target.value)}
          >
            <option value="">None</option>
            {projects.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.key} — {p.name}
              </option>
            ))}
          </select>
        </div>
        <button className="btn btn-primary" type="button" onClick={handleCreate} disabled={loading || !prompt.trim()}>
          {loading ? "Submitting…" : "Create run"}
        </button>
      </div>
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Governance runs</h2>
            <p>
              {runsTotal} total
              {runStats.running + runStats.queued > 0 ? (
                <>
                  {" "}
                  ·{" "}
                  <span className="runs-live-summary">
                    <span className="status-pulse-dot" aria-hidden="true" />
                    {runStats.running + runStats.queued} running
                  </span>
                </>
              ) : null}
            </p>
          </div>
        </div>
        <div className="workspace-toolbar">
          <div className="form-row">
            <label htmlFor="status-filter">Status filter</label>
            <select id="status-filter" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
              <option value="all">All</option>
              <option value="queued">Queued</option>
              <option value="running">Running</option>
              <option value="succeeded">Succeeded</option>
              <option value="failed">Failed</option>
            </select>
          </div>
          <div className="form-row">
            <label htmlFor="query-filter">Search</label>
            <input
              id="query-filter"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
              placeholder="Prompt text"
            />
          </div>
          <div className="form-row">
            <label htmlFor="run-project-filter">Project</label>
            <select
              id="run-project-filter"
              value={listProjectFilter}
              onChange={(e) => setListProjectFilter(e.target.value)}
            >
              <option value="">All projects</option>
              {projects.map((p) => (
                <option key={p.id} value={String(p.id)}>
                  {p.key} — {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <RunsListPanel
          runs={runs}
          selectedRunId={selectedRun?.id ?? null}
          onSelect={(id) => void handleSelectRun(id)}
          loading={listLoading}
        />
        <PaginationBar
          offset={offset}
          pageSize={pageSizeFromUrl}
          itemCount={runs.length}
          totalCount={runsTotal}
          onOffsetChange={(nextOffset) => setPage(Math.floor(nextOffset / pageSizeFromUrl) + 1)}
          onPageSizeChange={setPageSize}
        />
      </div>
      </div>
      <div className="master-detail-pane">
      {selectedRun ? (
        <div className="card master-detail-detail-card">
          <div className="runs-detail-header">
            <div>
              <span className="mono">#{selectedRun.id}</span>
              <span className={`status-chip status-chip--inline ${selectedRun.status}`}>
                {(selectedRun.status === "running" || selectedRun.status === "queued") && (
                  <span className="status-pulse-dot" aria-hidden="true" />
                )}
                {selectedRun.status}
              </span>
              <span className="workspace-meta">
                · {formatRelativeTime(selectedRun.finished_at ?? selectedRun.created_at)}
              </span>
            </div>
            <DeepLinkCopyBar path={selectedRunPath} />
          </div>
          <div className="detail-action-bar">
            <Link to={`/app/evidence?run_id=${selectedRun.id}`} className="btn btn-ghost btn-sm">
              Evidence
            </Link>
            <button className="btn btn-secondary btn-sm" type="button" onClick={() => setIsAgentDrawerOpen(true)}>
              View agent reasoning
            </button>
            <Link to={`/app/brief?run_id=${selectedRun.id}`} className="btn btn-primary btn-sm">
              View brief
            </Link>
            <button className="btn btn-ghost btn-sm" type="button" onClick={() => void exportSelectedRunPdf()}>
              Export PDF
            </button>
            <span className={`status-chip ${selectedRun.status}`}>{selectedRun.status}</span>
          </div>
          <div className="workspace-section-intro">
            <div>
              <h2>{selectedRun.prompt}</h2>
              <p>Detailed execution payload for investigation and explainability.</p>
            </div>
            <div className="actions" style={{ flexWrap: "wrap", gap: "0.5rem" }}>
              <button
                className="btn btn-ghost btn-sm"
                type="button"
                onClick={() => void copySignedShareLink()}
                disabled={selectedRun.status !== "succeeded"}
                title="JWT-signed URL: HTML snapshot + PDF one-pager, no sign-in until expiry"
              >
                Copy signed share URL
              </button>
              <button className="btn btn-ghost btn-sm" type="button" onClick={exportSelectedRunJson}>
                Export JSON
              </button>
              <button className="btn btn-primary btn-sm" type="button" onClick={exportSelectedRunCsv}>
                Export CSV
              </button>
              <button className="btn btn-primary btn-sm" type="button" onClick={exportSelectedRunPdf}>
                Export Brief (PDF)
              </button>
            </div>
          </div>
          <p className="mono" style={{ marginTop: 0 }}>
            status={selectedRun.status} · retries={selectedRun.retry_count}
            {selectedRun.portfolio_project_id != null
              ? ` · project=${projectById.get(selectedRun.portfolio_project_id)?.key ?? selectedRun.portfolio_project_id}`
              : ""}
          </p>
          {selectedRun.result_json &&
          typeof selectedRun.result_json === "object" &&
          selectedRun.result_json !== null &&
          ("decision_framing" in selectedRun.result_json || "utility" in selectedRun.result_json) ? (
            <div className="workspace-kpi-strip" style={{ marginBottom: "1rem" }}>
              {(() => {
                const df = ((selectedRun.result_json as { decision_framing?: unknown }).decision_framing ?? {}) as {
                  orchestration?: {
                    consensus_score?: number;
                    rar_triggered?: boolean;
                    rar_loops?: number;
                    recommended_action?: string;
                    utility_score?: number;
                    xi_score?: number;
                  };
                  findings_synthesis?: { consensus_score?: number; confidence?: number };
                  primary_recommendation_source?: string;
                };
                const o = df.orchestration;
                const f = df.findings_synthesis;
                const util = (selectedRun.result_json as { utility?: {
                  global_utility?: number;
                  perf_index?: number;
                  cost_index?: number;
                  risk_index?: number;
                } }).utility;
                const fmt = (v: number | undefined) => (v != null ? v.toFixed(2) : "—");
                return (
                  <>
                    <div className="metric">
                      <div className="label">Orchestration consensus</div>
                      <div className="value">{o?.consensus_score != null ? o.consensus_score.toFixed(2) : "—"}</div>
                    </div>
                    <div className="metric">
                      <div className="label">Findings synthesis</div>
                      <div className="value">{f?.consensus_score != null ? f.consensus_score.toFixed(2) : "—"}</div>
                    </div>
                    <div className="metric">
                      <div className="label">RAR</div>
                      <div className="value">{o?.rar_triggered ? `Yes (${o.rar_loops ?? 0})` : "No"}</div>
                    </div>
                    <div className="metric">
                      <div className="label">Action</div>
                      <div className="value mono" style={{ fontSize: "0.85rem" }}>
                        {String(o?.recommended_action ?? "—")}
                      </div>
                    </div>
                    <div className="metric">
                      <div className="label">Primary source</div>
                      <div className="value">{df.primary_recommendation_source ?? "—"}</div>
                    </div>
                    {util ? (
                      <>
                        <div className="metric">
                          <div className="label">Global U</div>
                          <div className="value">{fmt(util.global_utility)}</div>
                        </div>
                        <div className="metric">
                          <div className="label">P / Ci / R</div>
                          <div className="value mono" style={{ fontSize: "0.85rem" }}>
                            {fmt(util.perf_index)} / {fmt(util.cost_index)} / {fmt(util.risk_index)}
                          </div>
                        </div>
                      </>
                    ) : null}
                  </>
                );
              })()}
            </div>
          ) : null}
          <details className="accordion">
            <summary>Full run JSON</summary>
            <pre className="json-preview">{JSON.stringify(selectedRun.result_json, null, 2)}</pre>
          </details>
        </div>
      ) : (
        <div className="card master-detail-empty">
          <EmptyState>Select a run from the list to view details and actions.</EmptyState>
        </div>
      )}
      </div>
      </div>
      {isAgentDrawerOpen && parsedSelected ? (
        <>
          <div className="side-drawer-overlay" onClick={() => setIsAgentDrawerOpen(false)} />
          <div className="side-drawer">
            <div className="side-drawer-header">
              <h2>Agent Reasoning</h2>
              <button className="btn btn-ghost btn-sm" onClick={() => setIsAgentDrawerOpen(false)}>Close</button>
            </div>
            <div className="side-drawer-content">
              <AgentReasoningGrid
                agents={agentGrid}
                rarLoops={parsedSelected.result.rar?.rar_loops ?? 0}
              />
            </div>
          </div>
        </>
      ) : null}
    </WorkspacePageShell>
  );
}
