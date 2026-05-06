import { useEffect, useState } from "react";
import {
  fetchDecisionLifecycle,
  fetchConnectorConfigs,
  fetchDashboardSummary,
  fetchObservabilitySummary,
  fetchProviderConfigs,
  validateConnectorConfig,
  validateProviderConfig,
  type ConnectorConfig,
  type DashboardSummary,
  type DecisionLifecycle,
  type ObservabilitySummary,
  type ProviderConfig,
} from "../api";

type WorkspaceIntegrationsPageProps = {
  token: string;
  tenantSlug?: string | null;
  canManage: boolean;
};

function statusChip(ok: boolean | null) {
  if (ok == null) return "queued";
  return ok ? "succeeded" : "failed";
}

export function WorkspaceIntegrationsPage({ token, tenantSlug, canManage }: WorkspaceIntegrationsPageProps) {
  const [connectors, setConnectors] = useState<ConnectorConfig[]>([]);
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [obs, setObs] = useState<ObservabilitySummary | null>(null);
  const [lifecycle, setLifecycle] = useState<DecisionLifecycle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const notify = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2200);
  };

  const load = async () => {
    const [connectorRows, providerRows, telemetry, lifecycleSummary] = await Promise.all([
      fetchConnectorConfigs(token, tenantSlug),
      fetchProviderConfigs(token, tenantSlug),
      fetchDashboardSummary(token),
      fetchDecisionLifecycle(token),
    ]);
    const obsSummary = await fetchObservabilitySummary(token);
    setConnectors(connectorRows);
    setProviders(providerRows.providers);
    setSummary(telemetry);
    setObs(obsSummary);
    setLifecycle(lifecycleSummary);
  };

  useEffect(() => {
    load().catch((e) => setError(e instanceof Error ? e.message : "Failed to load integrations telemetry"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, tenantSlug]);

  const onValidateConnector = async (name: string) => {
    try {
      const row = await validateConnectorConfig(token, name, tenantSlug);
      setConnectors((prev) => prev.map((x) => (x.connector_name === name ? row : x)));
      notify(`${name} validated`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connector validation failed");
    }
  };

  const onValidateProvider = async (name: string) => {
    try {
      const row = await validateProviderConfig(token, name, tenantSlug);
      setProviders((prev) => prev.map((x) => (x.provider_name === name ? row : x)));
      notify(`${name} validated`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Provider validation failed");
    }
  };

  return (
    <div className="app">
      <header className="app-header workspace-page-head">
        <div className="brand">
          <h1>Integrations & Telemetry</h1>
          <span>Connector/provider health, validation, and runtime readiness</span>
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
          <div className="label">Connectors enabled</div>
          <div className="value">{summary ? `${summary.connectors_enabled}/${summary.connectors_total}` : "..."}</div>
        </div>
        <div className="metric">
          <div className="label">Providers enabled</div>
          <div className="value">{summary ? `${summary.providers_enabled}/${summary.providers_total}` : "..."}</div>
        </div>
        <div className="metric">
          <div className="label">Runs (24h)</div>
          <div className="value">{summary?.runs_24h ?? "..."}</div>
        </div>
        <div className="metric">
          <div className="label">Alerts (24h)</div>
          <div className="value bad">{summary?.alerts_24h ?? "..."}</div>
        </div>
        <div className="metric">
          <div className="label">Coverage</div>
          <div className="value">{summary ? `${summary.integration_coverage_pct}%` : "..."}</div>
        </div>
        <div className="metric">
          <div className="label">Freshness</div>
          <div className="value">{summary ? `${summary.integration_fresh_pct}%` : "..."}</div>
        </div>
      </div>

      <div className="workspace-split">
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Decision lifecycle intelligence</h2>
            <p>From telemetry and integration health to release posture and defendable governance outcomes.</p>
          </div>
        </div>
        <div className="settings-grid">
          <div className="metric">
            <div className="label">Release confidence</div>
            <div className={`value ${(lifecycle?.release.status ?? "review") === "go" ? "good" : "warn"}`}>
              {lifecycle ? `${(lifecycle.release.release_confidence * 100).toFixed(1)}%` : "..."}
            </div>
          </div>
          <div className="metric">
            <div className="label">Release status</div>
            <div className={`value ${(lifecycle?.release.status ?? "review") === "go" ? "good" : "warn"}`}>
              {lifecycle?.release.status ?? "..."}
            </div>
          </div>
          <div className="metric">
            <div className="label">Defendable outcome</div>
            <div className={`value ${lifecycle?.defendability.defendable ? "good" : "warn"}`}>
              {lifecycle ? (lifecycle.defendability.defendable ? "yes" : "review") : "..."}
            </div>
          </div>
          <div className="metric">
            <div className="label">Traceability score</div>
            <div className="value">{lifecycle ? lifecycle.defendability.outcome_traceability_score.toFixed(3) : "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Runs succeeded</div>
            <div className="value">
              {lifecycle ? `${lifecycle.governance.runs_succeeded}/${lifecycle.governance.runs_total}` : "..."}
            </div>
          </div>
          <div className="metric">
            <div className="label">Decisions approved</div>
            <div className="value">
              {lifecycle ? `${lifecycle.governance.decisions_approved}/${lifecycle.governance.decisions_total}` : "..."}
            </div>
          </div>
          <div className="metric">
            <div className="label">GitHub success rate</div>
            <div className="value">{lifecycle ? `${(lifecycle.release.github_success_rate * 100).toFixed(1)}%` : "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Jira blocked tickets</div>
            <div className="value warn">{lifecycle?.release.jira_blocked_tickets ?? "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Azure readiness</div>
            <div className={`value ${lifecycle?.release.azure_release_readiness === "green" ? "good" : "warn"}`}>
              {lifecycle?.release.azure_release_readiness ?? "..."}
            </div>
          </div>
        </div>
      </div>
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>System observability (5m)</h2>
            <p>Live platform pressure, latency posture, and short/long-window SLO burn signals.</p>
          </div>
        </div>
        <div className="settings-grid">
          <div className="metric">
            <div className="label">Req/min</div>
            <div className="value">{obs?.requests_per_min ?? "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Error rate</div>
            <div className="value bad">{obs ? `${(obs.error_rate * 100).toFixed(2)}%` : "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Latency p95</div>
            <div className="value">{obs ? `${obs.latency_ms_p95} ms` : "..."}</div>
          </div>
          <div className="metric">
            <div className="label">In-flight req</div>
            <div className="value">{obs?.inflight_requests ?? "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Run queue</div>
            <div className="value warn">{obs?.run_queue_depth ?? "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Run latency p95</div>
            <div className="value">{obs ? `${obs.run_latency_ms_p95} ms` : "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Connector calls</div>
            <div className="value">{obs?.connector_calls_total ?? "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Connector error rate</div>
            <div className="value bad">{obs ? `${(obs.connector_error_rate * 100).toFixed(2)}%` : "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Dead letters</div>
            <div className="value warn">{obs?.failure_recovery?.dead_letter_count ?? "..."}</div>
          </div>
        </div>
        <p className="field-hint">
          Prometheus format is available at <code>/api/v1/telemetry/observability/metrics</code> (authenticated).
        </p>
        <div className="settings-grid">
          <div className="metric">
            <div className="label">SLO target</div>
            <div className="value">{obs ? `${(obs.slo_burn_rate.target * 100).toFixed(2)}%` : "..."}</div>
          </div>
          <div className="metric">
            <div className="label">Burn rate (short)</div>
            <div className={`value ${obs?.slo_burn_rate.state === "critical" ? "bad" : obs?.slo_burn_rate.state === "warning" ? "warn" : "good"}`}>
              {obs ? obs.slo_burn_rate.short_burn_rate.toFixed(2) : "..."}
            </div>
          </div>
          <div className="metric">
            <div className="label">Burn rate (long)</div>
            <div className={`value ${obs?.slo_burn_rate.state === "critical" ? "bad" : obs?.slo_burn_rate.state === "warning" ? "warn" : "good"}`}>
              {obs ? obs.slo_burn_rate.long_burn_rate.toFixed(2) : "..."}
            </div>
          </div>
          <div className="metric">
            <div className="label">SLO state</div>
            <div className={`value ${obs?.slo_burn_rate.state === "critical" ? "bad" : obs?.slo_burn_rate.state === "warning" ? "warn" : "good"}`}>
              {obs?.slo_burn_rate.state ?? "..."}
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Connector telemetry</h2>
            <p>Health and validation posture of configured ingestion connectors.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Enabled</th>
                <th>Health</th>
                <th>Last checked</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {connectors.map((c) => (
                <tr key={c.connector_name}>
                  <td className="mono">{c.connector_name}</td>
                  <td>{c.enabled ? "Yes" : "No"}</td>
                  <td>
                    <span className={`status-chip ${statusChip(c.last_validation_ok)}`}>
                      {c.last_validation_ok == null ? "unknown" : c.last_validation_ok ? "healthy" : "failing"}
                    </span>
                  </td>
                  <td>{c.last_validated_at ? new Date(c.last_validated_at).toLocaleString() : "-"}</td>
                  <td>
                    <button
                      className="btn btn-ghost btn-sm"
                      type="button"
                      onClick={() => onValidateConnector(c.connector_name)}
                      disabled={!canManage}
                    >
                      Validate
                    </button>
                  </td>
                </tr>
              ))}
              {connectors.length === 0 ? (
                <tr>
                  <td colSpan={5} className="table-empty">
                    No connectors configured for this tenant scope.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
      </div>

      <div className="workspace-split">
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>AI provider telemetry</h2>
            <p>Validation readiness and runtime connectivity posture for each provider.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Enabled</th>
                <th>Health</th>
                <th>Last checked</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((p) => (
                <tr key={p.provider_name}>
                  <td className="mono">{p.provider_name}</td>
                  <td>{p.enabled ? "Yes" : "No"}</td>
                  <td>
                    <span className={`status-chip ${statusChip(p.last_validation_ok)}`}>
                      {p.last_validation_ok == null ? "unknown" : p.last_validation_ok ? "healthy" : "failing"}
                    </span>
                  </td>
                  <td>{p.last_validated_at ? new Date(p.last_validated_at).toLocaleString() : "-"}</td>
                  <td>
                    <button
                      className="btn btn-ghost btn-sm"
                      type="button"
                      onClick={() => onValidateProvider(p.provider_name)}
                      disabled={!canManage}
                    >
                      Validate
                    </button>
                  </td>
                </tr>
              ))}
              {providers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="table-empty">
                    No providers found in the current configuration.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Top endpoints (5m)</h2>
            <p>Most active routes and associated error pressure in current window.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Endpoint</th>
                <th>Requests</th>
                <th>Errors</th>
              </tr>
            </thead>
            <tbody>
              {(obs?.endpoints_top ?? []).map((row) => (
                <tr key={row.endpoint}>
                  <td className="mono">{row.endpoint}</td>
                  <td>{row.count}</td>
                  <td>{row.errors}</td>
                </tr>
              ))}
              {(obs?.endpoints_top ?? []).length === 0 ? (
                <tr>
                  <td colSpan={3} className="table-empty">
                    Endpoint telemetry appears once traffic is observed.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Alert rules</h2>
            <p>Rule evaluation outcomes over current telemetry and SLO burn posture.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Rule</th>
                <th>Status</th>
                <th>Severity</th>
                <th>Current</th>
                <th>Threshold</th>
              </tr>
            </thead>
            <tbody>
              {(obs?.alert_rules ?? []).map((rule) => (
                <tr key={rule.id}>
                  <td>{rule.name}</td>
                  <td>
                    <span className={`status-chip ${rule.triggered ? "failed" : "succeeded"}`}>
                      {rule.triggered ? "triggered" : "ok"}
                    </span>
                  </td>
                  <td>{rule.severity}</td>
                  <td>{rule.current_value}</td>
                  <td>{rule.threshold}</td>
                </tr>
              ))}
              {(obs?.alert_rules ?? []).length === 0 ? (
                <tr>
                  <td colSpan={5} className="table-empty">
                    No alert-rule evaluations available.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
      <div className="card">
        <div className="workspace-section-intro">
          <div>
            <h2>Tracing spans (recent)</h2>
            <p>Recent request traces for latency and failure-path diagnostics.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Span</th>
                <th>Duration</th>
                <th>Status</th>
                <th>Path</th>
              </tr>
            </thead>
            <tbody>
              {(obs?.spans_recent ?? []).slice().reverse().map((span, idx) => (
                <tr key={`${span.name}-${span.ts}-${idx}`}>
                  <td className="mono">{span.name}</td>
                  <td>{span.duration_ms.toFixed(2)} ms</td>
                  <td>
                    <span className={`status-chip ${span.status === "ok" ? "succeeded" : "failed"}`}>{span.status}</span>
                  </td>
                  <td className="mono">{String(span.attributes.path ?? "-")}</td>
                </tr>
              ))}
              {(obs?.spans_recent ?? []).length === 0 ? (
                <tr>
                  <td colSpan={4} className="table-empty">
                    No spans recorded in the current in-memory window.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
      </div>
    </div>
  );
}
