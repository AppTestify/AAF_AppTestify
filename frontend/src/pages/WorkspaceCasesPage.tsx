import { useEffect, useState } from "react";
import { approveDecision, createCase, createDecision, fetchCases, type Decision, type GovernanceCase } from "../api";

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

  const loadCases = async () => {
    const rows = await fetchCases(token);
    setCases(rows);
  };

  useEffect(() => {
    loadCases().catch((e) => setError(e instanceof Error ? e.message : "Failed to load cases"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

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
      const row = await createDecision(token, selectedCase.id, {
        recommended_action: "investigate",
        rationale: "Created from UI",
      });
      setDecision(row);
      setToast(`Decision #${row.id} created`);
      setTimeout(() => setToast(null), 2200);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create decision");
    }
  };

  const handleApproveDecision = async () => {
    if (!decision) return;
    try {
      const row = await approveDecision(token, decision.id, { final_action: "approved", rationale: "Approved in UI" });
      setDecision(row);
      setToast(`Decision #${row.id} approved`);
      setTimeout(() => setToast(null), 2200);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to approve decision");
    }
  };

  return (
    <div className="app">
      <header className="app-header">
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
      <div className="card">
        <h2>Create case</h2>
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
        <div className="form-row" style={{ maxWidth: 240 }}>
          <label htmlFor="case-status-filter">Status filter</label>
          <select id="case-status-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="all">All</option>
            <option value="new">New</option>
            <option value="in_review">In review</option>
            <option value="approved">Approved</option>
            <option value="closed">Closed</option>
          </select>
        </div>
        <div className="table-wrap">
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
              {cases
                .filter((c) => (statusFilter === "all" ? true : c.status === statusFilter))
                .map((c) => (
                  <tr key={c.id} onClick={() => setSelectedCase(c)}>
                    <td>#{c.id}</td>
                    <td>{c.title}</td>
                    <td>
                      <span className={`status-chip ${c.status}`}>{c.status}</span>
                    </td>
                    <td>{new Date(c.updated_at).toLocaleString()}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
      {selectedCase ? (
        <div className="card">
          <h2>Selected case #{selectedCase.id}</h2>
          <p className="mono">{selectedCase.title}</p>
          <div className="actions">
            <button className="btn btn-ghost" type="button" onClick={handleCreateDecision} disabled={!canManage}>
              Create decision
            </button>
            <button
              className="btn btn-primary"
              type="button"
              onClick={handleApproveDecision}
              disabled={!canManage || !decision}
            >
              Approve decision
            </button>
          </div>
          {decision ? (
            <pre style={{ overflow: "auto", maxHeight: 280 }}>{JSON.stringify(decision, null, 2)}</pre>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
