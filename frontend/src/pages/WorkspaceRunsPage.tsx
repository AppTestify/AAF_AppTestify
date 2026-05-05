import { useEffect, useMemo, useState } from "react";
import { createGovernanceRun, fetchGovernanceRun, fetchGovernanceRuns, type GovernanceRunV1 } from "../api";

type WorkspaceRunsPageProps = {
  token: string;
  tenantSlug?: string | null;
};

export function WorkspaceRunsPage({ token, tenantSlug }: WorkspaceRunsPageProps) {
  const [runs, setRuns] = useState<GovernanceRunV1[]>([]);
  const [prompt, setPrompt] = useState("");
  const [promptId, setPromptId] = useState("");
  const [selectedRun, setSelectedRun] = useState<GovernanceRunV1 | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [query, setQuery] = useState<string>("");
  const [toast, setToast] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeRunIds = useMemo(
    () => runs.filter((r) => r.status === "queued" || r.status === "running").map((r) => r.id),
    [runs]
  );

  const loadRuns = async () => {
    const list = await fetchGovernanceRuns(token, { limit: 100 });
    setRuns(list);
    if (selectedRun) {
      const next = list.find((r) => r.id === selectedRun.id);
      if (next) setSelectedRun(next);
    }
  };

  useEffect(() => {
    loadRuns().catch((e) => setError(e instanceof Error ? e.message : "Failed to load runs"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (activeRunIds.length === 0) return;
    const id = setInterval(() => {
      loadRuns().catch(() => undefined);
    }, 1200);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeRunIds.join(",")]);

  const handleCreate = async () => {
    if (!prompt.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const created = await createGovernanceRun(
        token,
        { prompt: prompt.trim(), prompt_id: promptId.trim() || null },
        tenantSlug
      );
      setPrompt("");
      setPromptId("");
      setSelectedRun(created);
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
    try {
      const row = await fetchGovernanceRun(token, runId);
      setSelectedRun(row);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load run");
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <h1>Runs</h1>
          <span>Asynchronous governance run history and details</span>
        </div>
      </header>
      {toast ? <div className="alert alert-success">{toast}</div> : null}
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      <div className="card">
        <h2>Create run</h2>
        <div className="form-row">
          <label htmlFor="run-prompt">Prompt</label>
          <textarea id="run-prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        </div>
        <div className="form-row">
          <label htmlFor="run-prompt-id">Prompt ID (optional)</label>
          <input id="run-prompt-id" value={promptId} onChange={(e) => setPromptId(e.target.value)} />
        </div>
        <button className="btn btn-primary" type="button" onClick={handleCreate} disabled={loading || !prompt.trim()}>
          {loading ? "Submitting…" : "Create run"}
        </button>
      </div>
      <div className="card">
        <h2>Run history</h2>
        <div className="settings-grid">
          <div className="form-row">
            <label htmlFor="status-filter">Status filter</label>
            <select id="status-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
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
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Prompt text"
            />
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Status</th>
                <th>Prompt</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {runs
                .filter((r) => (statusFilter === "all" ? true : r.status === statusFilter))
                .filter((r) => r.prompt.toLowerCase().includes(query.toLowerCase()))
                .map((r) => (
                  <tr key={r.id} onClick={() => handleSelectRun(r.id)}>
                    <td>#{r.id}</td>
                    <td>
                      <span className={`status-chip ${r.status}`}>{r.status}</span>
                    </td>
                    <td className="mono">{r.prompt.slice(0, 88)}</td>
                    <td>{new Date(r.created_at).toLocaleString()}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
      {selectedRun ? (
        <div className="card">
          <h2>Run detail #{selectedRun.id}</h2>
          <p className="mono" style={{ marginTop: 0 }}>
            status={selectedRun.status} · retries={selectedRun.retry_count}
          </p>
          <pre style={{ overflow: "auto", maxHeight: 320 }}>{JSON.stringify(selectedRun.result_json, null, 2)}</pre>
        </div>
      ) : null}
    </div>
  );
}
