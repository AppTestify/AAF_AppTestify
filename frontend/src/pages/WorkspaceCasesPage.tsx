import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  approveDecision,
  createCase,
  createDecision,
  fetchCasesAdvanced,
  fetchPortfolioProjects,
  type Decision,
  type GovernanceCase,
  type PortfolioProject,
} from "../api";
import { AuditTrailPanel } from "../components/governance/AuditTrailPanel";

type WorkspaceCasesPageProps = {
  tenantSlug?: string | null;
  canManage: boolean;
};

export function WorkspaceCasesPage({ tenantSlug, canManage }: WorkspaceCasesPageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const listProjectFilter = searchParams.get("portfolio_project_id") ?? "";
  const setListProjectFilter = (v: string) => {
    const next = new URLSearchParams(searchParams);
    if (v) next.set("portfolio_project_id", v);
    else next.delete("portfolio_project_id");
    setSearchParams(next, { replace: true });
  };

  const [cases, setCases] = useState<GovernanceCase[]>([]);
  const [projects, setProjects] = useState<PortfolioProject[]>([]);
  const [title, setTitle] = useState("");
  const [createProjectId, setCreateProjectId] = useState<string>("");
  const [selectedCase, setSelectedCase] = useState<GovernanceCase | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [offset, setOffset] = useState(0);
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
    loadCases()
      .then((rows) => {
        const caseId = searchParams.get("case_id");
        if (caseId) {
          const match = rows.find((c) => c.id === Number(caseId));
          if (match) setSelectedCase(match);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load cases"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, offset, query, listProjectFilter]);

  const loadCases = async (): Promise<GovernanceCase[]> => {
    try {
      setListLoading(true);
      const rows = await fetchCasesAdvanced({
        status: statusFilter === "all" ? undefined : statusFilter,
        limit: 50,
        offset,
        query: query || undefined,
        portfolio_project_id: listProjectFilter ? Number(listProjectFilter) : undefined,
      });
      setCases(rows);
      return rows;
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

  return (
    <div className="app">
      <header className="gov-hub-header">
        <p className="gov-hub-eyebrow">Decision & Audit</p>
        <h1 className="gov-hub-title">Formal decisions with audit-ready traceability</h1>
        <p className="gov-hub-lead">
          Open cases, propose recommendations, approve final actions, and review the full audit trail.
        </p>
      </header>

      <div className="gov-tabs">
        <button
          type="button"
          className={`btn btn-ghost btn-sm ${activeTab === "decisions" ? "active" : ""}`}
          onClick={() => setActiveTab("decisions")}
        >
          Decisions
        </button>
        <button
          type="button"
          className={`btn btn-ghost btn-sm ${activeTab === "audit" ? "active" : ""}`}
          onClick={() => setActiveTab("audit")}
        >
          Audit trail
        </button>
      </div>
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
      <div className="workspace-kpi-strip">
        <div className="metric">
          <div className="label">Visible cases</div>
          <div className="value">{cases.length}</div>
        </div>
        <div className="metric">
          <div className="label">New</div>
          <div className="value">{caseStats.draft}</div>
        </div>
        <div className="metric">
          <div className="label">In review</div>
          <div className="value warn">{caseStats.review}</div>
        </div>
        <div className="metric">
          <div className="label">Approved</div>
          <div className="value good">{caseStats.approved}</div>
        </div>
        <div className="metric">
          <div className="label">Closed</div>
          <div className="value">{caseStats.closed}</div>
        </div>
      </div>
      <div className="workspace-split">
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
          <div className="workspace-meta">Offset: {offset}</div>
        </div>
        <div className="workspace-toolbar">
          <div className="form-row">
            <label htmlFor="case-status-filter">Status filter</label>
            <select id="case-status-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="all">All</option>
              <option value="new">New</option>
              <option value="in_review">In review</option>
              <option value="approved">Approved</option>
              <option value="closed">Closed</option>
            </select>
          </div>
          <div className="form-row">
            <label htmlFor="case-query-filter">Search title</label>
            <input id="case-query-filter" value={query} onChange={(e) => setQuery(e.target.value)} />
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
          <button
            className="btn btn-ghost btn-sm"
            type="button"
            onClick={() => setOffset(Math.max(0, offset - 50))}
            disabled={offset === 0}
          >
            Prev
          </button>
          <button className="btn btn-ghost btn-sm" type="button" onClick={() => setOffset(offset + 50)} disabled={cases.length < 50}>
            Next
          </button>
          <span className="workspace-meta">Showing {cases.length} records</span>
        </div>
        <div className="table-wrap">
          {listLoading ? <div className="table-skeleton" /> : null}
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Project</th>
                <th>Status</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                  <tr key={c.id} onClick={() => setSelectedCase(c)} className={selectedCase?.id === c.id ? "row-selected" : ""}>
                    <td>#{c.id}</td>
                    <td>{c.title}</td>
                    <td className="mono">
                      {c.portfolio_project_id != null
                        ? projectById.get(c.portfolio_project_id)?.key ?? `#${c.portfolio_project_id}`
                        : "—"}
                    </td>
                    <td>
                      <span className={`status-chip ${c.status}`}>{c.status}</span>
                    </td>
                    <td>{new Date(c.updated_at).toLocaleString()}</td>
                  </tr>
                ))}
              {cases.length === 0 ? (
                <tr>
                  <td colSpan={5} className="table-empty">
                    No cases found for the current filters.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
      </div>
      {selectedCase ? (
        <div className="card">
          <div className="detail-header">
            <div>
              <h2>Selected case #{selectedCase.id}</h2>
              <p className="workspace-card-subtitle">Create a recommendation and finalize approval when ready.</p>
            </div>
            <span className={`status-chip ${selectedCase.status}`}>{selectedCase.status}</span>
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
          {decision ? <pre className="json-preview">{JSON.stringify(decision, null, 2)}</pre> : <div className="empty-state">No decision attached yet. Create a decision to continue approval workflow.</div>}
        </div>
      ) : null}
      </>
      ) : null}
    </div>
  );
}
