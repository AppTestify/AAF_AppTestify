import { useEffect, useMemo, useState } from "react";
import { NavLink, useSearchParams } from "react-router-dom";
import { DonutChart } from "../components/charts/DonutChart";
import { SegmentedTabs } from "../components/ui/SegmentedTabs";
import { DeepLinkCopyBar } from "../components/ui/DeepLinkCopyBar";
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

const PORTFOLIO_TABS = [
  { id: "projects", label: "Projects" },
  { id: "releases", label: "Releases" },
  { id: "operations", label: "Operations" },
  { id: "executive", label: "Executive report" },
] as const;

type PortfolioTab = (typeof PORTFOLIO_TABS)[number]["id"];

const OPS_LINKS: { to: string; label: string; blurb: string }[] = [
  { to: "/app/dashboard", label: "Dashboard", blurb: "Tenant KPIs, recent runs, connector health — same scope as the numbers below." },
  { to: "/app/overview", label: "Overview", blurb: "Run governance prompts and batch checks; feeds Runs and Evidence." },
  { to: "/app/runs", label: "Runs", blurb: "Every governance execution; link a release to a run via Run ID for traceability." },
  { to: "/app/evidence", label: "Evidence", blurb: "Connector snapshots captured on runs — proof for release decisions." },
  { to: "/app/cases", label: "Cases", blurb: "Structured reviews; decisions approved here roll into operational counts." },
  { to: "/app/alerts", label: "Alerts", blurb: "Audit-style events (24h count aligns with portfolio operations snapshot)." },
];

export function WorkspacePortfolioPage({ canManage }: WorkspacePortfolioPageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
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

  const [filterProjectId, setFilterProjectId] = useState<string>(
    () => searchParams.get("project_id") ?? "all"
  );
  const [activeTab, setActiveTab] = useState<PortfolioTab>(
    () => (searchParams.get("tab") as PortfolioTab) || "projects"
  );

  const syncUrlState = (patch: { projectId?: string; tab?: PortfolioTab }) => {
    const next = new URLSearchParams(searchParams);
    const projectId = patch.projectId ?? filterProjectId;
    const tab = patch.tab ?? activeTab;
    if (projectId && projectId !== "all") next.set("project_id", projectId);
    else next.delete("project_id");
    if (tab && tab !== "projects") next.set("tab", tab);
    else next.delete("tab");
    setSearchParams(next, { replace: true });
  };

  const syncProjectFilterToUrl = (v: string) => {
    setFilterProjectId(v);
    syncUrlState({ projectId: v });
  };

  const syncTabToUrl = (tab: PortfolioTab) => {
    setActiveTab(tab);
    syncUrlState({ tab });
  };

  const portfolioPath = useMemo(() => {
    const params = new URLSearchParams();
    if (filterProjectId && filterProjectId !== "all") params.set("project_id", filterProjectId);
    if (activeTab !== "projects") params.set("tab", activeTab);
    const qs = params.toString();
    return `/app/portfolio${qs ? `?${qs}` : ""}`;
  }, [filterProjectId, activeTab]);

  const syncReleaseProjectToUrl = (projectId: number) => {
    setReleaseProjectId(projectId);
    const next = new URLSearchParams(searchParams);
    if (projectId > 0) next.set("release_project_id", String(projectId));
    else next.delete("release_project_id");
    setSearchParams(next, { replace: true });
  };

  useEffect(() => {
    const releaseProjectIdParam = searchParams.get("release_project_id");
    if (releaseProjectIdParam) {
      const id = Number(releaseProjectIdParam);
      if (Number.isFinite(id) && id > 0) setReleaseProjectId(id);
    }
    const projectIdParam = searchParams.get("project_id");
    if (projectIdParam) setFilterProjectId(projectIdParam);
    const tabParam = searchParams.get("tab") as PortfolioTab | null;
    if (tabParam && PORTFOLIO_TABS.some((t) => t.id === tabParam)) setActiveTab(tabParam);
  }, [searchParams]);

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
      if (p.length > 0 && releaseProjectId === 0) {
        const fromUrl = Number(searchParams.get("release_project_id") || 0);
        setReleaseProjectId(fromUrl > 0 ? fromUrl : p[0].id);
      }
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

  const releaseStatusDonut = useMemo(() => {
    if (!report) return [];
    const other = Math.max(
      0,
      report.releases_total - report.releases_planned - report.releases_approved - report.releases_blocked
    );
    return [
      { name: "Planned", value: report.releases_planned, color: "#3d8bfd" },
      { name: "Go", value: report.releases_approved, color: "#22c55e" },
      { name: "Hold", value: report.releases_blocked, color: "#f59e0b" },
      ...(other > 0 ? [{ name: "Other", value: other, color: "#94a3b8" }] : []),
    ];
  }, [report]);

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

      <DeepLinkCopyBar path={portfolioPath} />
      <SegmentedTabs tabs={[...PORTFOLIO_TABS]} activeId={activeTab} onChange={(id) => syncTabToUrl(id as PortfolioTab)} />

      {activeTab === "projects" ? (
        <div className="card portfolio-projects-card">
          <div className="workspace-section-intro">
            <div>
              <h2>Projects</h2>
              <p>Select a project — selection syncs to the URL so refresh keeps context.</p>
            </div>
            {canManage ? (
              <button className="btn btn-primary btn-sm" type="button" onClick={() => document.getElementById("portfolio-add-project")?.scrollIntoView({ behavior: "smooth" })}>
                + New project
              </button>
            ) : null}
          </div>
          <div className="table-wrap">
            <table className="data-table portfolio-project-table">
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Status</th>
                  <th>Releases</th>
                </tr>
              </thead>
              <tbody>
                {projects.map((p) => {
                  const releaseCount = releases.filter((r) => r.project_id === p.id).length;
                  const isSelected = filterProjectId === String(p.id);
                  return (
                    <tr
                      key={p.id}
                      className={isSelected ? "portfolio-project-row--selected" : ""}
                      onClick={() => syncProjectFilterToUrl(String(p.id))}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") syncProjectFilterToUrl(String(p.id));
                      }}
                    >
                      <td>
                        <strong>{p.key}</strong> · {p.name}
                      </td>
                      <td>
                        <span className={`status-chip ${p.status === "active" ? "succeeded" : "queued"}`}>{p.status}</span>
                      </td>
                      <td>
                        {releaseCount} release{releaseCount === 1 ? "" : "s"} →
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {activeTab === "releases" ? (
        <div className="card">
          <div className="workspace-section-intro portfolio-release-head">
            <div>
              <h2>Release register</h2>
              <p>Filtered by selected project; open Runs to correlate run IDs.</p>
            </div>
            <div className="form-row portfolio-filter-row">
              <label htmlFor="portfolio-release-filter">Project</label>
              <select
                id="portfolio-release-filter"
                value={filterProjectId}
                onChange={(e) => syncProjectFilterToUrl(e.target.value)}
              >
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
                          <NavLink to={`/app/runs?run_id=${r.run_id}`} className="portfolio-inline-link">
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
      ) : null}

      {activeTab === "operations" ? (
        <>
          <div className="portfolio-kpi-section">
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
                <div className="label">Alerts (24h)</div>
                <div className="value warn">{ops?.alerts_24h ?? "…"}</div>
              </div>
              <div className="metric">
                <div className="label">Releases linked to runs</div>
                <div className="value">
                  {ops ? `${ops.portfolio_releases_linked_to_run} / ${ops.portfolio_releases_total} (${linkRate}%)` : "…"}
                </div>
              </div>
            </div>
          </div>
          <div className="card portfolio-explainer">
            <h2>How portfolio links to operations</h2>
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
        </>
      ) : null}

      {activeTab === "executive" ? (
        <>
          <div className="card portfolio-distribution">
            <h2>Release posture</h2>
            <div className="portfolio-chart-grid">
              <DonutChart data={releaseStatusDonut} title="Release status" emptyMessage="No releases in portfolio report yet." />
              <div className="portfolio-confidence-strip">
                <div className="metric">
                  <div className="label">Avg confidence</div>
                  <div className="value">{((report?.avg_confidence ?? 0) * 100).toFixed(1)}%</div>
                </div>
                <div className="metric">
                  <div className="label">Avg consensus</div>
                  <div className="value">{((report?.avg_consensus ?? 0) * 100).toFixed(1)}%</div>
                </div>
                <div className="metric">
                  <div className="label">Critical risk open</div>
                  <div className="value warn">{report?.high_risk_open ?? 0}</div>
                </div>
              </div>
            </div>
          </div>
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
        </>
      ) : null}

      {activeTab === "projects" ? (
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
      ) : null}

      {activeTab === "projects" ? (
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
      ) : null}

      {activeTab === "projects" && lifecycle ? (
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

      {activeTab === "projects" ? (
      <div className="card portfolio-distribution">
        <h2>Release posture</h2>
        <div className="portfolio-chart-grid">
          <DonutChart data={releaseStatusDonut} title="Release status" emptyMessage="No releases in portfolio report yet." />
          <div className="portfolio-confidence-strip">
            <div className="metric">
              <div className="label">Avg confidence</div>
              <div className="value">{((report?.avg_confidence ?? 0) * 100).toFixed(1)}%</div>
            </div>
            <div className="metric">
              <div className="label">Avg consensus</div>
              <div className="value">{((report?.avg_consensus ?? 0) * 100).toFixed(1)}%</div>
            </div>
            <div className="metric">
              <div className="label">Critical risk open</div>
              <div className="value warn">{report?.high_risk_open ?? 0}</div>
            </div>
            <div className="metric">
              <div className="label">Total releases</div>
              <div className="value">{report?.releases_total ?? 0}</div>
            </div>
          </div>
        </div>
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
      ) : null}

      {activeTab === "projects" && canManage ? (
        <div className="card-group">
          <div className="card" id="portfolio-add-project">
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
                <select value={releaseProjectId} onChange={(e) => syncReleaseProjectToUrl(Number(e.target.value))}>
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
    </div>
  );
}
