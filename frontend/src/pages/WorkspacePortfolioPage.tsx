import { useEffect, useMemo, useState } from "react";
import { NavLink } from "react-router-dom";
import {
  createPortfolioProject,
  createPortfolioRelease,
  fetchDecisionLifecycle,
  fetchExecutivePortfolioReport,
  fetchPortfolioOperationsContext,
  fetchPortfolioProjects,
  fetchPortfolioReleases,
  type DecisionLifecycle,
  type ExecutivePortfolioReport,
  type PortfolioOperationsContext,
  type PortfolioProject,
  type PortfolioRelease,
} from "../api";

type WorkspacePortfolioPageProps = {
  canManage: boolean;
};

const OPS_LINKS: { to: string; label: string; blurb: string }[] = [
  { to: "/app/dashboard", label: "Dashboard", blurb: "Tenant KPIs, recent runs, connector health — same scope as the numbers below." },
  { to: "/app/overview", label: "Overview", blurb: "Run governance prompts and batch checks; feeds Runs and Evidence." },
  { to: "/app/runs", label: "Runs", blurb: "Every governance execution; link a release to a run via Run ID for traceability." },
  { to: "/app/evidence", label: "Evidence", blurb: "Connector snapshots captured on runs — proof for release decisions." },
  { to: "/app/cases", label: "Cases", blurb: "Structured reviews; decisions approved here roll into operational counts." },
  { to: "/app/alerts", label: "Alerts", blurb: "Audit-style events (24h count aligns with portfolio operations snapshot)." },
];

export function WorkspacePortfolioPage({ canManage }: WorkspacePortfolioPageProps) {
  const [projects, setProjects] = useState<PortfolioProject[]>([]);
  const [releases, setReleases] = useState<PortfolioRelease[]>([]);
  const [report, setReport] = useState<ExecutivePortfolioReport | null>(null);
  const [ops, setOps] = useState<PortfolioOperationsContext | null>(null);
  const [lifecycle, setLifecycle] = useState<DecisionLifecycle | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [projectKey, setProjectKey] = useState("");
  const [projectName, setProjectName] = useState("");
  const [projectOwner, setProjectOwner] = useState("");

  const [releaseProjectId, setReleaseProjectId] = useState<number>(0);
  const [releaseVersion, setReleaseVersion] = useState("");
  const [releaseStatus, setReleaseStatus] = useState("planned");
  const [releaseDecision, setReleaseDecision] = useState("go");
  const [releaseRisk, setReleaseRisk] = useState("low");
  const [releaseTargetDate, setReleaseTargetDate] = useState("");
  const [releaseConfidence, setReleaseConfidence] = useState("");
  const [releaseConsensus, setReleaseConsensus] = useState("");
  const [releaseRunId, setReleaseRunId] = useState("");

  const [filterProjectId, setFilterProjectId] = useState<string>("all");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [p, r, summary, opCtx, lc] = await Promise.all([
        fetchPortfolioProjects(),
        fetchPortfolioReleases(),
        fetchExecutivePortfolioReport(),
        fetchPortfolioOperationsContext(),
        fetchDecisionLifecycle(),
      ]);
      setProjects(p);
      setReleases(r);
      setReport(summary);
      setOps(opCtx);
      setLifecycle(lc);
      if (p.length > 0 && releaseProjectId === 0) setReleaseProjectId(p[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load portfolio");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const filteredReleases = useMemo(() => {
    if (filterProjectId === "all") return releases;
    const id = Number(filterProjectId);
    return releases.filter((x) => x.project_id === id);
  }, [releases, filterProjectId]);

  const decisionMix = useMemo(() => {
    const m: Record<string, number> = {};
    for (const rel of releases) {
      const d = rel.release_decision ?? "unset";
      m[d] = (m[d] ?? 0) + 1;
    }
    return m;
  }, [releases]);

  const riskMix = useMemo(() => {
    const m: Record<string, number> = {};
    for (const rel of releases) {
      const r = rel.risk_level ?? "unset";
      m[r] = (m[r] ?? 0) + 1;
    }
    return m;
  }, [releases]);

  const addProject = async () => {
    if (!projectKey.trim() || !projectName.trim()) return;
    setError("");
    try {
      await createPortfolioProject({
        key: projectKey.trim(),
        name: projectName.trim(),
        owner: projectOwner.trim() || null,
        status: "active",
      });
      setProjectKey("");
      setProjectName("");
      setProjectOwner("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create project");
    }
  };

  const addRelease = async () => {
    if (!releaseProjectId || !releaseVersion.trim()) return;
    setError("");
    const conf = releaseConfidence.trim() === "" ? null : Number(releaseConfidence);
    const cons = releaseConsensus.trim() === "" ? null : Number(releaseConsensus);
    const runId = releaseRunId.trim() === "" ? null : Number(releaseRunId);
    let targetIso: string | null = null;
    if (releaseTargetDate.trim()) {
      const d = new Date(releaseTargetDate);
      if (!Number.isNaN(d.getTime())) targetIso = d.toISOString();
    }
    try {
      await createPortfolioRelease({
        project_id: releaseProjectId,
        version: releaseVersion.trim(),
        status: releaseStatus,
        release_decision: releaseDecision,
        risk_level: releaseRisk,
        target_date: targetIso,
        decision_confidence: conf !== null && !Number.isNaN(conf) ? conf : null,
        consensus_score: cons !== null && !Number.isNaN(cons) ? cons : null,
        run_id: runId !== null && !Number.isNaN(runId) ? runId : null,
      });
      setReleaseVersion("");
      setReleaseTargetDate("");
      setReleaseConfidence("");
      setReleaseConsensus("");
      setReleaseRunId("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create release");
    }
  };

  const linkRate =
    ops && ops.portfolio_releases_total > 0
      ? ((ops.portfolio_releases_linked_to_run / ops.portfolio_releases_total) * 100).toFixed(0)
      : "0";

  return (
    <div className="app portfolio-page">
      <header className="app-header workspace-page-head">
        <div className="brand">
          <h1>Portfolio &amp; releases</h1>
          <span>Executive program view, release register, and how it ties to day-to-day operations in the workspace.</span>
        </div>
      </header>
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      {loading ? <div className="card">Loading portfolio…</div> : null}

      <div className="card portfolio-explainer">
        <h2>How this works — and how it links to Operations</h2>
        <p className="portfolio-explainer-lead">
          <strong>Portfolio</strong> is a <em>program layer</em>: you define projects and releases (versions, decisions, risk, optional target
          dates). <strong>Operations</strong> is the <em>execution layer</em>: governance runs, evidence, cases, and alerts. Today they share the same{" "}
          <strong>tenant</strong> and can be tied together when you attach a <strong>Run ID</strong> to a release — otherwise the release record is
          planning metadata only.
        </p>
        <div className="portfolio-explainer-grid">
          <div className="portfolio-explainer-col">
            <h3>Portfolio (this page)</h3>
            <ul className="portfolio-bullet-list">
              <li>Projects (key, name, owner, status)</li>
              <li>Releases (version, decision, risk, dates, optional link to a governance run)</li>
              <li>Executive rollups: go/hold mix, confidence averages, high-risk flags</li>
            </ul>
          </div>
          <div className="portfolio-explainer-col">
            <h3>Operations (sidebar)</h3>
            <ul className="portfolio-bullet-list">
              <li>
                <NavLink to="/app/runs">Runs</NavLink> produce pipeline results and (via the worker) evidence and intelligence artifacts
              </li>
              <li>
                <NavLink to="/app/cases">Cases</NavLink> and decisions capture human approval workflows
              </li>
              <li>
                <NavLink to="/app/alerts">Alerts</NavLink> surface audit events; counts match the operations snapshot below
              </li>
            </ul>
          </div>
        </div>
        <div className="table-wrap portfolio-ops-link-table">
          <table className="data-table">
            <thead>
              <tr>
                <th>Operations area</th>
                <th>What it provides to portfolio decisions</th>
                <th>Open</th>
              </tr>
            </thead>
            <tbody>
              {OPS_LINKS.map((row) => (
                <tr key={row.to}>
                  <td>{row.label}</td>
                  <td>{row.blurb}</td>
                  <td>
                    <NavLink to={row.to} className="portfolio-inline-link">
                      Go →
                    </NavLink>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="portfolio-kpi-section">
        <h3 className="portfolio-kpi-heading">Program KPIs</h3>
        <div className="workspace-kpi-strip portfolio-kpi-strip">
          <div className="metric">
            <div className="label">Projects</div>
            <div className="value">{report?.projects_total ?? 0}</div>
          </div>
          <div className="metric">
            <div className="label">Active projects</div>
            <div className="value">{report?.active_projects ?? 0}</div>
          </div>
          <div className="metric">
            <div className="label">Releases</div>
            <div className="value">{report?.releases_total ?? 0}</div>
          </div>
          <div className="metric">
            <div className="label">Planned</div>
            <div className="value">{report?.releases_planned ?? 0}</div>
          </div>
          <div className="metric">
            <div className="label">Go decisions</div>
            <div className="value good">{report?.releases_approved ?? 0}</div>
          </div>
          <div className="metric">
            <div className="label">Hold decisions</div>
            <div className="value warn">{report?.releases_blocked ?? 0}</div>
          </div>
          <div className="metric">
            <div className="label">Avg confidence</div>
            <div className="value">{((report?.avg_confidence ?? 0) * 100).toFixed(1)}%</div>
          </div>
          <div className="metric">
            <div className="label">Avg consensus</div>
            <div className="value">{((report?.avg_consensus ?? 0) * 100).toFixed(1)}%</div>
          </div>
          <div className="metric">
            <div className="label">Critical risk</div>
            <div className="value warn">{report?.high_risk_open ?? 0}</div>
          </div>
        </div>

        <h3 className="portfolio-kpi-heading">Operations snapshot (same tenant as Dashboard)</h3>
        <div className="workspace-kpi-strip portfolio-kpi-strip">
          <div className="metric">
            <div className="label">Runs (total)</div>
            <div className="value">{ops?.runs_total ?? "…"}</div>
          </div>
          <div className="metric">
            <div className="label">Runs (24h)</div>
            <div className="value">{ops?.runs_24h ?? "…"}</div>
          </div>
          <div className="metric">
            <div className="label">Succeeded (24h)</div>
            <div className="value good">{ops?.runs_success_24h ?? "…"}</div>
          </div>
          <div className="metric">
            <div className="label">Open cases</div>
            <div className="value">{ops?.cases_open ?? "…"}</div>
          </div>
          <div className="metric">
            <div className="label">Cases (total)</div>
            <div className="value">{ops?.cases_total ?? "…"}</div>
          </div>
          <div className="metric">
            <div className="label">Alerts (24h)</div>
            <div className="value warn">{ops?.alerts_24h ?? "…"}</div>
          </div>
          <div className="metric">
            <div className="label">Evidence rows</div>
            <div className="value">{ops?.evidence_snapshots_total ?? "…"}</div>
          </div>
          <div className="metric">
            <div className="label">Decisions / approved</div>
            <div className="value">
              {ops ? `${ops.decisions_total} / ${ops.decisions_approved}` : "…"}
            </div>
          </div>
          <div className="metric">
            <div className="label">Releases linked to runs</div>
            <div className="value">
              {ops ? `${ops.portfolio_releases_linked_to_run} / ${ops.portfolio_releases_total} (${linkRate}%)` : "…"}
            </div>
          </div>
        </div>
      </div>

      {lifecycle ? (
        <div className="card portfolio-lifecycle-card">
          <h2>Decision lifecycle (Integrations + telemetry)</h2>
          <p className="workspace-meta">
            Pulled from the same decision-lifecycle service used on Integrations — release confidence and defendability for leadership narrative.
          </p>
          <div className="workspace-kpi-strip">
            <div className="metric">
              <div className="label">Release confidence</div>
              <div className="value">{(lifecycle.release.release_confidence * 100).toFixed(1)}%</div>
            </div>
            <div className="metric">
              <div className="label">Release status</div>
              <div className="value">{lifecycle.release.status}</div>
            </div>
            <div className="metric">
              <div className="label">Traceability</div>
              <div className="value">{(lifecycle.defendability.outcome_traceability_score * 100).toFixed(0)}%</div>
            </div>
            <div className="metric">
              <div className="label">Defendable</div>
              <div className="value">{lifecycle.defendability.defendable ? "yes" : "no"}</div>
            </div>
            <div className="metric">
              <div className="label">Runs succeeded</div>
              <div className="value">{lifecycle.governance.runs_succeeded}</div>
            </div>
            <div className="metric">
              <div className="label">GitHub success rate</div>
              <div className="value">{(lifecycle.release.github_success_rate * 100).toFixed(1)}%</div>
            </div>
          </div>
          <NavLink to="/app/integrations" className="portfolio-inline-link">
            Configure connectors and view full lifecycle →
          </NavLink>
        </div>
      ) : null}

      <div className="card portfolio-distribution">
        <h2>Release posture</h2>
        <div className="portfolio-distribution-cols">
          <div>
            <h3>Decisions</h3>
            {Object.keys(decisionMix).length === 0 ? (
              <p className="workspace-meta">No releases yet.</p>
            ) : (
              <ul className="portfolio-mix-list">
                {Object.entries(decisionMix).map(([k, v]) => (
                  <li key={k}>
                    <span className="portfolio-mix-key">{k}</span>
                    <span className="portfolio-mix-val">{v}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h3>Risk levels</h3>
            {Object.keys(riskMix).length === 0 ? (
              <p className="workspace-meta">No releases yet.</p>
            ) : (
              <ul className="portfolio-mix-list">
                {Object.entries(riskMix).map(([k, v]) => (
                  <li key={k}>
                    <span className="portfolio-mix-key">{k}</span>
                    <span className="portfolio-mix-val">{v}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {canManage ? (
        <div className="card-group">
          <div className="card">
            <h2>Add project</h2>
            <p className="workspace-meta">Stable program identifier (key) and display name. Does not auto-create runs — use Overview / Runs for execution.</p>
            <div className="config-columns">
              <div className="form-row">
                <label>Project key</label>
                <input value={projectKey} onChange={(e) => setProjectKey(e.target.value)} placeholder="PAYMENTS" />
              </div>
              <div className="form-row">
                <label>Project name</label>
                <input value={projectName} onChange={(e) => setProjectName(e.target.value)} placeholder="Payments Platform" />
              </div>
              <div className="form-row">
                <label>Owner</label>
                <input value={projectOwner} onChange={(e) => setProjectOwner(e.target.value)} placeholder="VP Engineering" />
              </div>
            </div>
            <div className="actions">
              <button className="btn btn-primary" type="button" onClick={addProject}>
                Create project
              </button>
            </div>
          </div>
          <div className="card">
            <h2>Add release</h2>
            <p className="workspace-meta">
              Optional <strong>Run ID</strong> ties this release to a specific governance run (find IDs under{" "}
              <NavLink to="/app/runs">Runs</NavLink>). Confidence/consensus can mirror pipeline output for reporting.
            </p>
            <div className="config-columns">
              <div className="form-row">
                <label>Project</label>
                <select value={releaseProjectId} onChange={(e) => setReleaseProjectId(Number(e.target.value))}>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.key} — {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-row">
                <label>Version</label>
                <input value={releaseVersion} onChange={(e) => setReleaseVersion(e.target.value)} placeholder="2026.05.1" />
              </div>
              <div className="form-row">
                <label>Target date</label>
                <input type="datetime-local" value={releaseTargetDate} onChange={(e) => setReleaseTargetDate(e.target.value)} />
              </div>
              <div className="form-row">
                <label>Status</label>
                <select value={releaseStatus} onChange={(e) => setReleaseStatus(e.target.value)}>
                  <option value="planned">planned</option>
                  <option value="in_review">in_review</option>
                  <option value="released">released</option>
                </select>
              </div>
              <div className="form-row">
                <label>Decision</label>
                <select value={releaseDecision} onChange={(e) => setReleaseDecision(e.target.value)}>
                  <option value="go">go</option>
                  <option value="hold">hold</option>
                  <option value="review">review</option>
                </select>
              </div>
              <div className="form-row">
                <label>Risk</label>
                <select value={releaseRisk} onChange={(e) => setReleaseRisk(e.target.value)}>
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                  <option value="critical">critical</option>
                </select>
              </div>
              <div className="form-row">
                <label>Decision confidence (0–1)</label>
                <input value={releaseConfidence} onChange={(e) => setReleaseConfidence(e.target.value)} placeholder="0.85" />
              </div>
              <div className="form-row">
                <label>Consensus score (0–1)</label>
                <input value={releaseConsensus} onChange={(e) => setReleaseConsensus(e.target.value)} placeholder="0.78" />
              </div>
              <div className="form-row">
                <label>Governance run ID (optional)</label>
                <input value={releaseRunId} onChange={(e) => setReleaseRunId(e.target.value)} placeholder="e.g. 42" />
              </div>
            </div>
            <div className="actions">
              <button className="btn btn-primary" type="button" onClick={addRelease}>
                Create release
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="card">
        <h2>Executive project breakdown</h2>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Project</th>
                <th>Owner</th>
                <th>Status</th>
                <th>Releases</th>
                <th>Go</th>
                <th>Hold</th>
                <th>Avg confidence</th>
              </tr>
            </thead>
            <tbody>
              {(report?.project_breakdown ?? []).map((row) => {
                const proj = projects.find((x) => x.id === row.project_id);
                return (
                  <tr key={row.project_id}>
                    <td>
                      {row.project_key} — {row.project_name}
                    </td>
                    <td>{proj?.owner ?? "—"}</td>
                    <td>{proj?.status ?? "—"}</td>
                    <td>{row.releases_total}</td>
                    <td>{row.go_count}</td>
                    <td>{row.hold_count}</td>
                    <td>{(row.avg_confidence * 100).toFixed(1)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h2>Project directory</h2>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Key</th>
                <th>Name</th>
                <th>Owner</th>
                <th>Status</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id}>
                  <td>{p.key}</td>
                  <td>{p.name}</td>
                  <td>{p.owner ?? "—"}</td>
                  <td>{p.status}</td>
                  <td>{new Date(p.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="workspace-section-intro portfolio-release-head">
          <div>
            <h2>Release register</h2>
            <p>Filter by project; open <NavLink to="/app/runs">Runs</NavLink> to correlate run IDs.</p>
          </div>
          <div className="form-row portfolio-filter-row">
            <label htmlFor="portfolio-release-filter">Filter</label>
            <select id="portfolio-release-filter" value={filterProjectId} onChange={(e) => setFilterProjectId(e.target.value)}>
              <option value="all">All projects</option>
              {projects.map((p) => (
                <option key={p.id} value={String(p.id)}>
                  {p.key}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Project</th>
                <th>Version</th>
                <th>Target</th>
                <th>Status</th>
                <th>Decision</th>
                <th>Conf.</th>
                <th>Consensus</th>
                <th>Risk</th>
                <th>Run</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {filteredReleases.slice(0, 100).map((r) => {
                const p = projects.find((x) => x.id === r.project_id);
                return (
                  <tr key={r.id}>
                    <td>{p ? p.key : r.project_id}</td>
                    <td>{r.version}</td>
                    <td>{r.target_date ? new Date(r.target_date).toLocaleString() : "—"}</td>
                    <td>{r.status}</td>
                    <td>{r.release_decision ?? "—"}</td>
                    <td>{r.decision_confidence != null ? (r.decision_confidence * 100).toFixed(0) + "%" : "—"}</td>
                    <td>{r.consensus_score != null ? (r.consensus_score * 100).toFixed(0) + "%" : "—"}</td>
                    <td>{r.risk_level ?? "—"}</td>
                    <td>
                      {r.run_id != null ? (
                        <NavLink to="/app/runs" className="portfolio-inline-link" title="Open Runs to locate this run ID">
                          #{r.run_id}
                        </NavLink>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>{new Date(r.updated_at).toLocaleString()}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
