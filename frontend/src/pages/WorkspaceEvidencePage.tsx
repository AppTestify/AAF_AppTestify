import { useEffect, useState } from "react";
import { fetchEvidence, type EvidenceRow } from "../api";

type WorkspaceEvidencePageProps = {
  token: string;
};

export function WorkspaceEvidencePage({ token }: WorkspaceEvidencePageProps) {
  const [rows, setRows] = useState<EvidenceRow[]>([]);
  const [connector, setConnector] = useState<string>("");
  const [runId, setRunId] = useState<string>("");
  const [selected, setSelected] = useState<EvidenceRow | null>(null);
  const [error, setError] = useState<string>("");
  const [listLoading, setListLoading] = useState(false);

  useEffect(() => {
    setListLoading(true);
    fetchEvidence(token, { connector: connector || undefined, run_id: runId ? Number(runId) : undefined, limit: 200 })
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load evidence"))
      .finally(() => setListLoading(false));
  }, [token, connector, runId]);

  return (
    <div className="app">
      <header className="app-header workspace-page-head">
        <div className="brand">
          <h1>Evidence</h1>
          <span>Connector evidence snapshots with payload inspection for triage and audits.</span>
        </div>
      </header>
      {error ? <div className="alert alert-error">{error}</div> : null}
      <div className="card">
        <h2>Evidence & History</h2>
        <div className="workspace-toolbar">
          <div className="form-row">
            <label htmlFor="connector-filter">Connector filter</label>
            <select id="connector-filter" value={connector} onChange={(e) => setConnector(e.target.value)}>
              <option value="">All</option>
              <option value="github">GitHub</option>
              <option value="jira">Jira</option>
              <option value="azure">Azure</option>
              <option value="aws">AWS</option>
              <option value="finops">FinOps</option>
            </select>
          </div>
          <div className="form-row">
            <label htmlFor="run-filter">Run ID</label>
            <input id="run-filter" value={runId} onChange={(e) => setRunId(e.target.value)} placeholder="optional" />
          </div>
        </div>
        <div className="table-wrap">
          {listLoading ? <div className="table-skeleton" /> : null}
          <table className="data-table">
            <thead>
              <tr>
                <th>Run</th>
                <th>Connector</th>
                <th>Captured</th>
                <th>Payload</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} onClick={() => setSelected(r)} className={selected?.id === r.id ? "row-selected" : ""}>
                  <td>#{r.run_id}</td>
                  <td>
                    <span className="status-chip queued">{r.connector_name}</span>
                  </td>
                  <td>{new Date(r.created_at).toLocaleString()}</td>
                  <td className="mono">{JSON.stringify(r.payload_json).slice(0, 120)}</td>
                </tr>
              ))}
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={4} className="table-empty">
                    No evidence rows found for the current filters.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
      {selected ? (
        <div className="card">
          <h2>Evidence detail #{selected.id}</h2>
          <p className="workspace-card-subtitle">
            Connector <span className="mono">{selected.connector_name}</span> · run #{selected.run_id}
          </p>
          <pre className="json-preview">{JSON.stringify(selected.payload_json, null, 2)}</pre>
        </div>
      ) : null}
    </div>
  );
}
