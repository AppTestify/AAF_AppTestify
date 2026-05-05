import { useEffect, useState } from "react";
import { fetchAuditEvents, type AuditEvent } from "../api";

type WorkspaceAlertsPageProps = {
  token: string;
};

export function WorkspaceAlertsPage({ token }: WorkspaceAlertsPageProps) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAuditEvents(token)
      .then(setEvents)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load audit events"));
  }, [token]);

  return (
    <div className="app">
      <header className="app-header">
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
      <div className="card">
        <h2>Recent events</h2>
        <ul className="list-plain">
          {events.map((e) => (
            <li key={e.id}>
              <span className="mono">
                {e.area}/{e.action}
              </span>{" "}
              — {e.summary}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
