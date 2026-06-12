import { useEffect, useMemo, useState } from "react";
import { acknowledgeAlert, fetchAuditEvents, type AuditEvent } from "../api";
import { WorkspacePageShell } from "../components/layout/WorkspacePageShell";
import { PaginationBar } from "../components/ui/PaginationBar";

type WorkspaceAlertsPageProps = {
  };

const DEFAULT_PAGE_SIZE = 50;

export function WorkspaceAlertsPage({}: WorkspaceAlertsPageProps) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [area, setArea] = useState<string>("");
  const [severity, setSeverity] = useState<string>("");
  const [selected, setSelected] = useState<AuditEvent | null>(null);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [listLoading, setListLoading] = useState(false);
  const [ackLoadingId, setAckLoadingId] = useState<number | null>(null);
  const [offset, setOffset] = useState(0);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

  const alertStats = useMemo(() => {
    const info = events.filter((e) => e.severity === "info").length;
    const warning = events.filter((e) => e.severity === "warning").length;
    const critical = events.filter((e) => e.severity === "critical").length;
    return { info, warning, critical };
  }, [events]);

  const loadEvents = () =>
    fetchAuditEvents({
      area: area || undefined,
      severity: severity || undefined,
      limit: pageSize,
      offset,
    });

  useEffect(() => {
    setOffset(0);
  }, [area, severity]);

  useEffect(() => {
    setListLoading(true);
    loadEvents()
      .then((page) => {
        setEvents(page.items);
        setTotal(page.total);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load audit events"))
      .finally(() => setListLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [area, severity, offset, pageSize]);

  const onAcknowledge = async (id: number) => {
    try {
      setAckLoadingId(id);
      await acknowledgeAlert(id);
      const page = await loadEvents();
      setEvents(page.items);
      setTotal(page.total);
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
      await Promise.all(events.map((e) => acknowledgeAlert(e.id)));
      const page = await loadEvents();
      setEvents(page.items);
      setTotal(page.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Bulk acknowledge failed");
    } finally {
      setBulkLoading(false);
    }
  };

  return (
    <WorkspacePageShell
      variant="operational"
      title="Alerts & Audit"
      subtitle="Recent governance and configuration actions"
    >
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      <div className="workspace-kpi-strip">
        <div className="metric">
          <div className="label">Matching alerts</div>
          <div className="value">{total}</div>
        </div>
        <div className="metric">
          <div className="label">Critical (page)</div>
          <div className="value bad">{alertStats.critical}</div>
        </div>
        <div className="metric">
          <div className="label">Warning (page)</div>
          <div className="value warn">{alertStats.warning}</div>
        </div>
        <div className="metric">
          <div className="label">Info (page)</div>
          <div className="value">{alertStats.info}</div>
        </div>
      </div>
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Recent events</h2>
            <p>Triage audit and governance signals with bulk or individual acknowledge actions.</p>
          </div>
          <div className="workspace-meta">
            {total} matching · showing {events.length} on this page
          </div>
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
        <PaginationBar
          offset={offset}
          pageSize={pageSize}
          itemCount={events.length}
          totalCount={total}
          onOffsetChange={setOffset}
          onPageSizeChange={setPageSize}
        />
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
    </WorkspacePageShell>
  );
}
