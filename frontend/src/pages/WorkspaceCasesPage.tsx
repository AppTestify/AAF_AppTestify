import { useEffect, useMemo, useState } from "react";
import { approveDecision, createCase, createDecision, fetchCasesAdvanced, type Decision, type GovernanceCase } from "../api";

type WorkspaceCasesPageProps = {
  token: string;
  tenantSlug?: string | null;
  canManage: boolean;
};

export function WorkspaceCasesPage({ token, tenantSlug, canManage }: WorkspaceCasesPageProps) {
  const [cases, setCases] = useState<GovernanceCase[]>([]);
  const [title, setTitle] = useState("");
  const [selectedCase, setSelectedCase] = useState<GovernanceCase | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [offset, setOffset] = useState(0);
  const [query, setQuery] = useState("");
  const [listLoading, setListLoading] = useState(false);
  const [decisionLoading, setDecisionLoading] = useState(false);
  const caseStats = useMemo(() => {
    const draft = cases.filter((c) => c.status === "new").length;
    const review = cases.filter((c) => c.status === "in_review").length;
    const approved = cases.filter((c) => c.status === "approved").length;
    const closed = cases.filter((c) => c.status === "closed").length;
    return { draft, review, approved, closed };
  }, [cases]);

  const loadCases = async () => {
    try {
      setListLoading(true);
      const rows = await fetchCasesAdvanced(token, {
        status: statusFilter === "all" ? undefined : statusFilter,
        limit: 50,
        offset,
        query: query || undefined,
      });
      setCases(rows);
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    loadCases().catch((e) => setError(e instanceof Error ? e.message : "Failed to load cases"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, statusFilter, offset, query]);

  const handleCreateCase = async () => {
    if (!title.trim()) return;
    try {
      const row = await createCase(token, { title: title.trim() }, tenantSlug);
      setTitle("");
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
      const row = await createDecision(token, selectedCase.id, {
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
      const row = await approveDecision(token, decision.id, { final_action: "approved", rationale: "Approved in UI" });
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
      <header className="app-header workspace-page-head">
        <div className="brand">
          <h1>Cases & Decisions</h1>
          <span>Track governance lifecycle from case creation to approval</span>
        </div>
      </header>
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      {toast ? <div className="alert alert-success">{toast}</div> : null}
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
                <th>Status</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                  <tr key={c.id} onClick={() => setSelectedCase(c)} className={selectedCase?.id === c.id ? "row-selected" : ""}>
                    <td>#{c.id}</td>
                    <td>{c.title}</td>
                    <td>
                      <span className={`status-chip ${c.status}`}>{c.status}</span>
                    </td>
                    <td>{new Date(c.updated_at).toLocaleString()}</td>
                  </tr>
                ))}
              {cases.length === 0 ? (
                <tr>
                  <td colSpan={4} className="table-empty">
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
    </div>
  );
}
