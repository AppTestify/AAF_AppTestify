import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  approveDecision,
  createCase,
  createDecision,
  createGovernanceRunShareLink,
  exportRunBriefPdf,
  fetchCase,
  fetchCasesAdvanced,
  fetchPortfolioProjects,
  type Decision,
  type GovernanceCase,
  type PortfolioProject,
} from "../api";
import { AuditTrailPanel } from "../components/governance/AuditTrailPanel";
import { GovernanceFlowStepper } from "../components/governance/GovernanceFlowStepper";
import { WorkspacePageShell } from "../components/layout/WorkspacePageShell";
import { DataTable } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/EmptyState";
import { KpiStrip } from "../components/ui/KpiStrip";
import { PaginationBar } from "../components/ui/PaginationBar";
import { SegmentedTabs } from "../components/ui/SegmentedTabs";

type WorkspaceCasesPageProps = {
  tenantSlug?: string | null;
  canManage: boolean;
};

export function WorkspaceCasesPage({ tenantSlug, canManage }: WorkspaceCasesPageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const listProjectFilter = searchParams.get("portfolio_project_id") ?? "";
  const runIdParam = searchParams.get("run_id") ?? "";
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

  const setListProjectFilter = (v: string) => {
    const next = new URLSearchParams(searchParams);
    if (v) next.set("portfolio_project_id", v);
    else next.delete("portfolio_project_id");
    next.delete("page");
    setSearchParams(next, { replace: true });
  };

  const [cases, setCases] = useState<GovernanceCase[]>([]);
  const [casesTotal, setCasesTotal] = useState(0);
  const [projects, setProjects] = useState<PortfolioProject[]>([]);
  const [title, setTitle] = useState("");
  const [createProjectId, setCreateProjectId] = useState<string>("");
  const [selectedCase, setSelectedCase] = useState<GovernanceCase | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [listLoading, setListLoading] = useState(false);
  const [decisionLoading, setDecisionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"decisions" | "audit">("decisions");
  const projectById = useMemo(() => {
    const m = new Map<number, PortfolioProject>();
    for (const p of projects) m.set(p.id, p);
    return m;
  }, [projects]);

  const caseStats = useMemo(() => {
    const draft = cases.filter((c) => c.status === "new").length;
    const review = cases.filter((c) => c.status === "in_review").length;
    const approved = cases.filter((c) => c.status === "approved").length;
    const closed = cases.filter((c) => c.status === "closed").length;
    return { draft, review, approved, closed };
  }, [cases]);

  useEffect(() => {
    fetchPortfolioProjects()
      .then(setProjects)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load portfolio projects"));
  }, []);

  useEffect(() => {
    const caseId = searchParams.get("case_id");
    if (!caseId) return;
    const id = Number(caseId);
    if (!Number.isFinite(id)) return;
    fetchCase(id)
      .then(setSelectedCase)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load case from link"));
  }, [searchParams.get("case_id")]);

  useEffect(() => {
    loadCases()
      .then((rows) => {
        const caseId = searchParams.get("case_id");
        if (caseId) return;
        if (runIdParam) {
          const runId = Number(runIdParam);
          const match = rows.find((c) => c.latest_run_id === runId);
          if (match) setSelectedCase(match);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load cases"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, offset, query, listProjectFilter, pageSizeFromUrl]);

  const loadCases = async (): Promise<GovernanceCase[]> => {
    try {
      setListLoading(true);
      const page = await fetchCasesAdvanced({
        status: statusFilter === "all" ? undefined : statusFilter,
        limit: pageSizeFromUrl,
        offset,
        query: query || undefined,
        portfolio_project_id: listProjectFilter ? Number(listProjectFilter) : undefined,
      });
      setCases(page.items);
      setCasesTotal(page.total);
      return page.items;
    } finally {
      setListLoading(false);
    }
  };

  const handleCreateCase = async () => {
    if (!title.trim()) return;
    try {
      const row = await createCase({
          title: title.trim(),
          portfolio_project_id: createProjectId ? Number(createProjectId) : null,
        },
        tenantSlug
      );
      setTitle("");
      setCreateProjectId("");
      setSelectedCase(row);
      setToast(`Case #${row.id} created`);
      setTimeout(() => setToast(null), 2200);
      await loadCases();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create case");
    }
  };

  const handleCreateDecision = async () => {
    if (!selectedCase) return;
    try {
      setDecisionLoading(true);
      const row = await createDecision(selectedCase.id, {
        recommended_action: "investigate",
        rationale: "Created from UI",
      });
      setDecision(row);
      setToast(`Decision #${row.id} created`);
      setTimeout(() => setToast(null), 2200);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create decision");
    } finally {
      setDecisionLoading(false);
    }
  };

  const handleApproveDecision = async () => {
    if (!decision) return;
    try {
      setDecisionLoading(true);
      const row = await approveDecision(decision.id, { final_action: "approved", rationale: "Approved in UI" });
      setDecision(row);
      setToast(`Decision #${row.id} approved`);
      setTimeout(() => setToast(null), 2200);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to approve decision");
    } finally {
      setDecisionLoading(false);
    }
  };

  const selectedRunId = selectedCase?.latest_run_id ?? null;

  const copyCaseShareLink = () => {
    if (!selectedCase) return;
    const url = `${window.location.origin}/app/cases?case_id=${selectedCase.id}`;
    void navigator.clipboard.writeText(url);
    setToast("Case link copied");
    setTimeout(() => setToast(null), 2200);
  };

  const exportCaseBriefPdf = async () => {
    if (!selectedRunId) return;
    try {
      const blob = await exportRunBriefPdf(selectedRunId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `governance_brief_${selectedRunId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      setToast("Export Brief PDF downloaded");
      setTimeout(() => setToast(null), 2200);
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF export failed");
    }
  };

  const copySignedRunShare = async () => {
    if (!selectedRunId) return;
    try {
      const { url } = await createGovernanceRunShareLink(selectedRunId);
      await navigator.clipboard.writeText(url);
      setToast("Signed share URL copied");
      setTimeout(() => setToast(null), 2500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create share link");
    }
  };

  return (
    <WorkspacePageShell
      variant="governance"
      eyebrow="Decision & Audit"
      title="Formal decisions with audit-ready traceability"
      subtitle="Open cases, propose recommendations, approve final actions, and review the full audit trail."
    >
      {runIdParam && Number.isFinite(Number(runIdParam)) ? (
        <GovernanceFlowStepper runId={Number(runIdParam)} activeStep="cases" />
      ) : null}

      <SegmentedTabs
        tabs={[
          { id: "decisions", label: "Decisions" },
          { id: "audit", label: "Audit trail" },
        ]}
        activeId={activeTab}
        onChange={(id) => setActiveTab(id as "decisions" | "audit")}
      />
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      {toast ? <div className="alert alert-success">{toast}</div> : null}
      {activeTab === "audit" ? (
        <div className="card">
          <AuditTrailPanel />
        </div>
      ) : null}

      {activeTab === "decisions" ? (
      <>
      <KpiStrip
        items={[
          { label: "Visible cases", value: cases.length },
          { label: "New", value: caseStats.draft },
          { label: "In review", value: caseStats.review, tone: "warn" },
          { label: "Approved", value: caseStats.approved, tone: "good" },
          { label: "Closed", value: caseStats.closed },
        ]}
      />
      <div className="master-detail-layout">
      <div className="master-detail-list">
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Create case</h2>
            <p>Open governance cases and track decision progression.</p>
          </div>
          <div className="workspace-meta">Case creation is tenant-scoped</div>
        </div>
        <div className="form-row">
          <label htmlFor="case-title" className="field-label-required">Title</label>
          <input id="case-title" value={title} onChange={(e) => setTitle(e.target.value)} disabled={!canManage} />
        </div>
        <div className="form-row">
          <label htmlFor="case-portfolio-project">Portfolio project (optional)</label>
          <select
            id="case-portfolio-project"
            value={createProjectId}
            onChange={(e) => setCreateProjectId(e.target.value)}
            disabled={!canManage}
          >
            <option value="">None</option>
            {projects.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.key} — {p.name}
              </option>
            ))}
          </select>
        </div>
        <button className="btn btn-primary" type="button" disabled={!canManage || !title.trim()} onClick={handleCreateCase}>
          Create case
        </button>
      </div>
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Cases</h2>
            <p>Filter and triage cases before creating or approving decisions.</p>
          </div>
        </div>
        <div className="workspace-toolbar">
          <div className="form-row">
            <label htmlFor="case-status-filter">Status filter</label>
            <select id="case-status-filter" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
              <option value="all">All</option>
              <option value="new">New</option>
              <option value="in_review">In review</option>
              <option value="approved">Approved</option>
              <option value="closed">Closed</option>
            </select>
          </div>
          <div className="form-row">
            <label htmlFor="case-query-filter">Search title</label>
            <input id="case-query-filter" value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} />
          </div>
          <div className="form-row">
            <label htmlFor="case-project-filter">Project</label>
            <select
              id="case-project-filter"
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
        <DataTable
          columns={[
            { key: "id", header: "ID", render: (row) => `#${row.id}` },
            { key: "title", header: "Title", render: (row) => row.title },
            {
              key: "project",
              header: "Project",
              className: "mono",
              render: (row) =>
                row.portfolio_project_id != null
                  ? projectById.get(row.portfolio_project_id)?.key ?? `#${row.portfolio_project_id}`
                  : "—",
            },
            {
              key: "status",
              header: "Status",
              render: (row) => <span className={`status-chip ${row.status}`}>{row.status}</span>,
            },
            {
              key: "updated",
              header: "Updated",
              render: (row) => new Date(row.updated_at).toLocaleString(),
            },
          ]}
          rows={cases}
          rowKey={(row) => row.id}
          loading={listLoading}
          selectedRowKey={selectedCase?.id ?? null}
          onRowClick={setSelectedCase}
          emptyMessage="No cases found for the current filters."
        />
        <PaginationBar
          offset={offset}
          pageSize={pageSizeFromUrl}
          itemCount={cases.length}
          totalCount={casesTotal}
          onOffsetChange={(nextOffset) => setPage(Math.floor(nextOffset / pageSizeFromUrl) + 1)}
          onPageSizeChange={setPageSize}
        />
      </div>
      </div>
      <div className="master-detail-pane">
      {selectedCase ? (
        <div className="card master-detail-detail-card">
          <div className="detail-action-bar">
            {selectedRunId ? (
              <Link to={`/app/evidence?run_id=${selectedRunId}`} className="btn btn-ghost btn-sm">
                Evidence
              </Link>
            ) : (
              <button className="btn btn-ghost btn-sm" type="button" disabled>
                Evidence
              </button>
            )}
            {selectedRunId ? (
              <Link to={`/app/brief?run_id=${selectedRunId}`} className="btn btn-primary btn-sm">
                Brief
              </Link>
            ) : (
              <button className="btn btn-primary btn-sm" type="button" disabled>
                Brief
              </button>
            )}
            <button
              className="btn btn-ghost btn-sm"
              type="button"
              onClick={() => void exportCaseBriefPdf()}
              disabled={!selectedRunId}
            >
              Export PDF
            </button>
            <button className="btn btn-ghost btn-sm" type="button" onClick={() => void copySignedRunShare()} disabled={!selectedRunId}>
              Share
            </button>
            <button className="btn btn-ghost btn-sm" type="button" onClick={copyCaseShareLink}>
              Copy case link
            </button>
            <span className={`status-chip ${selectedCase.status}`}>{selectedCase.status}</span>
          </div>
          <div className="detail-header">
            <div>
              <h2>Selected case #{selectedCase.id}</h2>
              <p className="workspace-card-subtitle">Create a recommendation and finalize approval when ready.</p>
            </div>
          </div>
          <p className="mono">{selectedCase.title}</p>
          {selectedCase.portfolio_project_id != null ? (
            <p className="workspace-meta mono">
              Project:{" "}
              {projectById.get(selectedCase.portfolio_project_id)?.key ?? `#${selectedCase.portfolio_project_id}`}
            </p>
          ) : null}
          <div className="actions">
            <button className="btn btn-ghost" type="button" onClick={handleCreateDecision} disabled={!canManage || decisionLoading}>
              {decisionLoading ? "Processing…" : "Create decision"}
            </button>
            <button
              className="btn btn-primary"
              type="button"
              onClick={handleApproveDecision}
              disabled={!canManage || !decision || decisionLoading}
            >
              {decisionLoading ? "Processing…" : "Approve decision"}
            </button>
          </div>
          {decision ? <pre className="json-preview">{JSON.stringify(decision, null, 2)}</pre> : (
            <EmptyState>No decision attached yet. Create a decision to continue approval workflow.</EmptyState>
          )}
        </div>
      ) : (
        <div className="card master-detail-empty">
          <EmptyState>Select a case from the list to review decisions and audit actions.</EmptyState>
        </div>
      )}
      </div>
      </div>
      </>
      ) : null}
    </WorkspacePageShell>
  );
}
