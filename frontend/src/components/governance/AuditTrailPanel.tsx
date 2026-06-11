import { useEffect, useState } from "react";
import { acknowledgeAlert, fetchAuditEvents, type AuditEvent } from "../../api";

export function AuditTrailPanel() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [area, setArea] = useState("");
  const [severity, setSeverity] = useState("");
  const [selected, setSelected] = useState<AuditEvent | null>(null);
  const [listLoading, setListLoading] = useState(false);
  const [ackLoadingId, setAckLoadingId] = useState<number | null>(null);

  const load = () => {
    setListLoading(true);
    fetchAuditEvents({ area: area || undefined, severity: severity || undefined, limit: 200 })
      .then(setEvents)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load audit events"))
      .finally(() => setListLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [area, severity]);

  const onAcknowledge = async (id: number) => {
    try {
      setAckLoadingId(id);
      await acknowledgeAlert(id);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Acknowledge failed");
    } finally {
      setAckLoadingId(null);
    }
  };

  return (
    <div>
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      <div className="workspace-toolbar">
        <div className="form-row">
          <label htmlFor="audit-area-filter">Area</label>
          <input id="audit-area-filter" value={area} onChange={(e) => setArea(e.target.value)} placeholder="governance_run" />
        </div>
        <div className="form-row">
          <label htmlFor="audit-severity-filter">Severity</label>
          <select id="audit-severity-filter" value={severity} onChange={(e) => setSeverity(e.target.value)}>
            <option value="">All</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>
        </div>
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
                    disabled={ackLoadingId === e.id}
                  >
                    {ackLoadingId === e.id ? "Ack…" : "Ack"}
                  </button>
                </td>
              </tr>
            ))}
            {events.length === 0 ? (
              <tr>
                <td colSpan={5} className="table-empty">
                  No audit events for the current filters.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      {selected ? (
        <pre className="json-preview" style={{ marginTop: "1rem" }}>
          {JSON.stringify(selected, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}
