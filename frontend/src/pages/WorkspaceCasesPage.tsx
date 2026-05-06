import { useEffect, useState } from "react";
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
      <div className="workspace-split">
      <div className="card">
        <h2>Create case</h2>
        <p className="workspace-card-subtitle">Open governance cases and track decision progression.</p>
        <div className="form-row">
          <label htmlFor="case-title">Title</label>
          <input id="case-title" value={title} onChange={(e) => setTitle(e.target.value)} disabled={!canManage} />
        </div>
        <button className="btn btn-primary" type="button" disabled={!canManage || !title.trim()} onClick={handleCreateCase}>
          Create case
        </button>
      </div>
      <div className="card">
        <h2>Cases</h2>
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
          <span className="mono">offset={offset}</span>
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
          <h2>Selected case #{selectedCase.id}</h2>
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
          {decision ? (
            <pre className="json-preview">{JSON.stringify(decision, null, 2)}</pre>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
