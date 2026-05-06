import { useEffect, useMemo, useState } from "react";
import { acknowledgeAlert, fetchAuditEvents, type AuditEvent } from "../api";

type WorkspaceAlertsPageProps = {
  token: string;
};

export function WorkspaceAlertsPage({ token }: WorkspaceAlertsPageProps) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [area, setArea] = useState<string>("");
  const [severity, setSeverity] = useState<string>("");
  const [selected, setSelected] = useState<AuditEvent | null>(null);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [listLoading, setListLoading] = useState(false);
  const [ackLoadingId, setAckLoadingId] = useState<number | null>(null);
  const alertStats = useMemo(() => {
    const info = events.filter((e) => e.severity === "info").length;
    const warning = events.filter((e) => e.severity === "warning").length;
    const critical = events.filter((e) => e.severity === "critical").length;
    return { info, warning, critical };
  }, [events]);

  useEffect(() => {
    setListLoading(true);
    fetchAuditEvents(token, { area: area || undefined, severity: severity || undefined, limit: 200 })
      .then(setEvents)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load audit events"))
      .finally(() => setListLoading(false));
  }, [token, area, severity]);

  const onAcknowledge = async (id: number) => {
    try {
      setAckLoadingId(id);
      await acknowledgeAlert(token, id);
      const next = await fetchAuditEvents(token, { area: area || undefined, severity: severity || undefined, limit: 200 });
      setEvents(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Acknowledge failed");
    } finally {
      setAckLoadingId(null);
    }
  };

  const onAcknowledgeVisible = async () => {
    if (events.length === 0) return;
    setBulkLoading(true);
    setError(null);
    try {
      await Promise.all(events.map((e) => acknowledgeAlert(token, e.id)));
      const next = await fetchAuditEvents(token, { area: area || undefined, severity: severity || undefined, limit: 200 });
      setEvents(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Bulk acknowledge failed");
    } finally {
      setBulkLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header workspace-page-head">
        <div className="brand">
          <h1>Alerts & Audit</h1>
          <span>Recent governance and configuration actions</span>
        </div>
      </header>
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      <div className="workspace-kpi-strip">
        <div className="metric">
          <div className="label">Visible alerts</div>
          <div className="value">{events.length}</div>
        </div>
        <div className="metric">
          <div className="label">Critical</div>
          <div className="value bad">{alertStats.critical}</div>
        </div>
        <div className="metric">
          <div className="label">Warning</div>
          <div className="value warn">{alertStats.warning}</div>
        </div>
        <div className="metric">
          <div className="label">Info</div>
          <div className="value">{alertStats.info}</div>
        </div>
      </div>
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Recent events</h2>
            <p>Triage audit and governance signals with bulk or individual acknowledge actions.</p>
          </div>
          <div className="workspace-meta">Last {events.length} events shown</div>
        </div>
        <div className="workspace-toolbar">
          <div className="form-row">
            <label htmlFor="area-filter">Area filter</label>
            <input id="area-filter" value={area} onChange={(e) => setArea(e.target.value)} placeholder="governance_run" />
          </div>
          <div className="form-row">
            <label htmlFor="severity-filter">Severity</label>
            <select id="severity-filter" value={severity} onChange={(e) => setSeverity(e.target.value)}>
              <option value="">All</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <button className="btn btn-ghost btn-sm" type="button" onClick={onAcknowledgeVisible} disabled={bulkLoading || events.length === 0}>
            {bulkLoading ? "Acknowledging…" : "Acknowledge visible"}
          </button>
        </div>
        <div className="table-wrap">
          {listLoading ? <div className="table-skeleton" /> : null}
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Area/Action</th>
                <th>Summary</th>
                <th>Time</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id} onClick={() => setSelected(e)} className={selected?.id === e.id ? "row-selected" : ""}>
                  <td>#{e.id}</td>
                  <td className="mono">
                    {e.area}/{e.action}
                  </td>
                  <td>{e.summary}</td>
                  <td>{new Date(e.created_at).toLocaleString()}</td>
                  <td>
                    <button
                      className="btn btn-ghost btn-sm"
                      type="button"
                      onClick={() => onAcknowledge(e.id)}
                      disabled={ackLoadingId === e.id || bulkLoading}
                    >
                      {ackLoadingId === e.id ? "Ack…" : "Ack"}
                    </button>
                  </td>
                </tr>
              ))}
              {events.length === 0 ? (
                <tr>
                  <td colSpan={5} className="table-empty">
                    No alerts found for the current filters.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
      {selected ? (
        <div className="card">
          <div className="detail-header">
            <div>
              <h2>Alert detail #{selected.id}</h2>
              <p className="workspace-card-subtitle">Expanded event payload for forensic traceability.</p>
            </div>
            <span className={`status-chip ${selected.severity === "critical" ? "failed" : selected.severity === "warning" ? "running" : "queued"}`}>
              {selected.severity}
            </span>
          </div>
          <pre className="json-preview">{JSON.stringify(selected, null, 2)}</pre>
        </div>
      ) : null}
    </div>
  );
}
