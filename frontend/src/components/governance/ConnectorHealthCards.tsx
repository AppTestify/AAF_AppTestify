import { Link } from "react-router-dom";
import type { DashboardSummary } from "../../api";
import { formatRelativeTime } from "../../lib/governancePresentation";

type ConnectorHealthCardsProps = {
  connectors?: DashboardSummary["connector_health"];
};

function statusLabel(c: DashboardSummary["connector_health"][number]): {
  text: string;
  tone: "good" | "bad" | "warn" | "muted";
} {
  if (!c.enabled) return { text: "disabled", tone: "muted" };
  if (c.last_validation_ok === true) {
    const when = c.last_validated_at ? formatRelativeTime(c.last_validated_at) : "recently";
    return { text: `valid · ${when}`, tone: "good" };
  }
  if (c.last_validation_ok === false) {
    const err = (c.last_validation_error ?? "auth error").toLowerCase();
    if (err.includes("auth") || err.includes("401") || err.includes("403") || err.includes("credential")) {
      return { text: "auth error", tone: "bad" };
    }
    return { text: c.last_validation_error?.slice(0, 40) ?? "validation failed", tone: "bad" };
  }
  return { text: "not validated", tone: "warn" };
}

export function ConnectorHealthCards({ connectors = [] }: ConnectorHealthCardsProps) {
  if (!connectors.length) {
    return (
      <div className="card connector-health-cards">
        <h3>Connector health</h3>
        <p className="workspace-meta">No connectors configured.</p>
        <Link to="/app/integrations" className="btn btn-ghost btn-sm">
          Configure integrations →
        </Link>
      </div>
    );
  }

  return (
    <div className="card connector-health-cards">
      <div className="workspace-section-intro">
        <div>
          <h3>Connector health</h3>
          <p className="workspace-meta">Auth and validation failures surface here immediately.</p>
        </div>
        <Link to="/app/integrations" className="btn btn-ghost btn-sm">
          Settings
        </Link>
      </div>
      <div className="connector-health-grid">
        {connectors.map((c) => {
          const st = statusLabel(c);
          return (
            <div key={c.connector_name} className={`connector-health-card connector-health-card--${st.tone}`}>
              <strong>{c.connector_name}</strong>
              <span className={`connector-health-status connector-health-status--${st.tone}`}>{st.text}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
