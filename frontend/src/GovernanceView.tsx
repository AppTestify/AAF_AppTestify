import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import type {
  AgentOpinion,
  GovernanceRunResult,
  PromptLibrary,
  TenantRow,
  UserPublic,
  UtilityResult,
} from "./api";
import { formatAgentLabel } from "./api";

export type GovernanceViewProps = {
  user: UserPublic;
  error: string | null;
  tenants: TenantRow[] | null;
  newTenantName: string;
  setNewTenantName: (v: string) => void;
  newTenantSlug: string;
  setNewTenantSlug: (v: string) => void;
  onCreateTenant: (e: React.FormEvent) => void | Promise<void>;
  prompt: string;
  setPrompt: (v: string) => void;
  promptId: string | null;
  setPromptId: (v: string | null) => void;
  library: PromptLibrary | null;
  applyLibraryPrompt: (id: string) => void;
  onRunGovernance: () => void | Promise<void>;
  onBatch: () => void | Promise<void>;
  loading: boolean;
  result: GovernanceRunResult | null;
  batchResult: unknown;
};

function AgentOpinionCard({ opinion }: { opinion: AgentOpinion }) {
  const evidence = opinion.evidence ?? [];
  const hasSignals = opinion.raw_signals && Object.keys(opinion.raw_signals).length > 0;

  return (
    <li className="agent-opinion-card">
      <div className="agent-opinion-head">
        <strong>{formatAgentLabel(opinion.agent_id)}</strong>
        <span className="status-chip running">{opinion.risk_theme.replace(/_/g, " ")}</span>
        <span className="field-hint">confidence {opinion.confidence.toFixed(2)}</span>
      </div>
      <p style={{ margin: "0.35rem 0 0.5rem" }}>{opinion.claim}</p>
      {evidence.length > 0 ? (
        <ul className="list-plain agent-evidence-list">
          {evidence.map((line, idx) => (
            <li key={idx}>{line}</li>
          ))}
        </ul>
      ) : null}
      {hasSignals ? (
        <details className="accordion agent-signals-accordion">
          <summary>Tool signals</summary>
          <pre className="json-preview">{JSON.stringify(opinion.raw_signals, null, 2)}</pre>
        </details>
      ) : null}
    </li>
  );
}

export function GovernanceView(props: GovernanceViewProps) {
  const {
    user,
    error,
    tenants,
    newTenantName,
    setNewTenantName,
    newTenantSlug,
    setNewTenantSlug,
    onCreateTenant,
    prompt,
    setPrompt,
    promptId,
    setPromptId,
    library,
    applyLibraryPrompt,
    onRunGovernance,
    onBatch,
    loading,
    result,
    batchResult,
  } = props;

  const pmView = result?.pm_view;
  const consensus = result?.consensus;
  const rar = result?.rar;
  const utility: UtilityResult | undefined = result?.utility;
  const xi = result?.explainability?.xi_score;
  const framing = result?.decision_framing as
    | {
        orchestration?: { consensus_score?: number };
        findings_synthesis?: { consensus_score?: number; confidence?: number };
        primary_recommendation_source?: string;
      }
    | undefined;

  const consensusScore = consensus?.consensus_score ?? null;
  const orchConsensus = framing?.orchestration?.consensus_score ?? consensusScore;
  const findingsConsensus = framing?.findings_synthesis?.consensus_score ?? null;

  const scoreClass = useMemo(() => {
    const v = orchConsensus;
    if (v == null) return "";
    if (v >= 0.65) return "good";
    if (v >= 0.45) return "warn";
    return "bad";
  }, [orchConsensus]);

  const [activeResultTab, setActiveResultTab] = useState<"executive" | "evidence" | "agents" | "explainability">(
    "executive"
  );

  const formatIndex = (v: number | undefined) => (v != null && !Number.isNaN(v) ? v.toFixed(2) : "—");

  return (
    <div className="app">
      <header className="app-header workspace-page-head">
        <div className="brand">
          <h1>Governance overview</h1>
          <span>
            Signed in as {user.email}
            {user.is_superadmin ? " · superadmin" : user.tenant_slug ? ` · tenant: ${user.tenant_slug}` : ""}
          </span>
        </div>
      </header>

      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}

      {user.is_superadmin && tenants ? (
        <div className="card">
          <h2>Tenants (superadmin)</h2>
          <ul className="list-plain" style={{ marginBottom: "1rem" }}>
            {tenants.map((t) => (
              <li key={t.id}>
                <span className="mono">{t.slug}</span> — {t.name}{" "}
                <span style={{ color: "var(--muted)" }}>({t.user_count} users)</span>
              </li>
            ))}
          </ul>
          <form onSubmit={onCreateTenant}>
            <div className="form-row">
              <label htmlFor="tname">New tenant name</label>
              <input
                id="tname"
                value={newTenantName}
                onChange={(e) => setNewTenantName(e.target.value)}
                placeholder="Acme Corp"
              />
            </div>
            <div className="form-row">
              <label htmlFor="tslug">Slug (lowercase, hyphens ok)</label>
              <input
                id="tslug"
                className="mono"
                value={newTenantSlug}
                onChange={(e) => setNewTenantSlug(e.target.value)}
                placeholder="acme"
              />
            </div>
            <button className="btn btn-ghost" type="submit" disabled={loading}>
              Add tenant
            </button>
          </form>
        </div>
      ) : null}

      <div className="workspace-split">
        <div className="card">
          <div className="workspace-section-intro">
            <div>
              <h2>Compose request</h2>
              <p>Select a prompt template or write a custom governance question.</p>
            </div>
            <div className="workspace-meta">Prompt routing follows tenant AI config defaults</div>
          </div>
          <div className="form-row">
            <label htmlFor="library">Prompt library</label>
            <select
              id="library"
              value={promptId ?? ""}
              onChange={(e) => {
                const v = e.target.value;
                if (v) applyLibraryPrompt(v);
                else {
                  setPromptId(null);
                }
              }}
            >
              <option value="">— Custom prompt —</option>
              {(library?.prompts ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label htmlFor="prompt" className="field-label-required">
              Question
            </label>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Are we safe to release based on GitHub activity?"
            />
          </div>
          <div className="actions">
            <button
              className="btn btn-primary"
              type="button"
              disabled={loading || !prompt.trim()}
              onClick={onRunGovernance}
            >
              {loading ? "Running…" : "Run governance"}
            </button>
            {user.is_superadmin || user.is_admin ? (
              <button className="btn btn-ghost" type="button" disabled={loading} onClick={onBatch}>
                Run batch (library)
              </button>
            ) : null}
          </div>
        </div>
        {result ? (
          <div className="card">
            <div className="workspace-section-intro">
              <div>
                <h2>Decision snapshot</h2>
                <p>Live result posture from the latest governance execution.</p>
              </div>
            </div>
            <div className="metrics">
              <div className="metric">
                <div className="label">Orchestration consensus</div>
                <div className={`value ${scoreClass}`}>
                  {orchConsensus != null ? Number(orchConsensus).toFixed(2) : "—"}
                </div>
              </div>
              {findingsConsensus != null ? (
                <div className="metric">
                  <div className="label">Findings synthesis</div>
                  <div className="value">{findingsConsensus.toFixed(2)}</div>
                </div>
              ) : null}
              <div className="metric">
                <div className="label">Global U</div>
                <div className="value">{formatIndex(utility?.global_utility)}</div>
              </div>
              <div className="metric">
                <div className="label">P / Ci / R</div>
                <div className="value mono" style={{ fontSize: "0.85rem" }}>
                  {formatIndex(utility?.perf_index)} / {formatIndex(utility?.cost_index)} /{" "}
                  {formatIndex(utility?.risk_index)}
                </div>
              </div>
              <div className="metric">
                <div className="label">RAR</div>
                <div className="value">{rar?.rar_triggered ? `Yes (${rar.rar_loops})` : "No"}</div>
              </div>
              <div className="metric">
                <div className="label">Action</div>
                <div className="value mono" style={{ fontSize: "0.85rem" }}>
                  {utility?.recommended_action ?? "—"}
                </div>
              </div>
              <div className="metric">
                <div className="label">XI</div>
                <div className="value">{xi != null ? xi.toFixed(2) : "—"}</div>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {batchResult ? (
        <div className="card">
          <div className="workspace-section-intro">
            <div>
              <h2>Batch results</h2>
              <p>Execution output from library-scale governance runs.</p>
            </div>
          </div>
          <pre className="mono" style={{ fontSize: "0.8rem", overflow: "auto" }}>
            {JSON.stringify(batchResult, null, 2)}
          </pre>
        </div>
      ) : null}

      {result ? (
        <div className="card">
          <div className="workspace-toolbar">
            <button
              className={`btn btn-ghost btn-sm ${activeResultTab === "executive" ? "active" : ""}`}
              type="button"
              onClick={() => setActiveResultTab("executive")}
            >
              Executive
            </button>
            <button
              className={`btn btn-ghost btn-sm ${activeResultTab === "evidence" ? "active" : ""}`}
              type="button"
              onClick={() => setActiveResultTab("evidence")}
            >
              Evidence
            </button>
            <button
              className={`btn btn-ghost btn-sm ${activeResultTab === "agents" ? "active" : ""}`}
              type="button"
              onClick={() => setActiveResultTab("agents")}
            >
              Agents
            </button>
            <button
              className={`btn btn-ghost btn-sm ${activeResultTab === "explainability" ? "active" : ""}`}
              type="button"
              onClick={() => setActiveResultTab("explainability")}
            >
              Explainability
            </button>
          </div>
          {activeResultTab === "executive" ? (
            <>
              <div className="workspace-section-intro">
                <div>
                  <h2>Executive view</h2>
                  <p>Business-facing summary and decision narrative for stakeholder communication.</p>
                </div>
              </div>
              {pmView ? (
                <>
                  <p style={{ margin: "0 0 0.5rem", fontWeight: 600 }}>{pmView.title}</p>
                  <div className="pm-summary">
                    <ReactMarkdown>{pmView.summary_markdown}</ReactMarkdown>
                  </div>
                </>
              ) : null}
              <p className="field-hint">Connectors: {result.connectors_used?.join(", ") || "—"}</p>
            </>
          ) : null}
          {activeResultTab === "evidence" ? (
            <div className="workspace-split">
              <div>
                <h2>Normalized evidence</h2>
                {result.normalized_evidence?.length ? (
                  <ul className="list-plain">
                    {result.normalized_evidence.map((e, i) => {
                      const url = e.metadata?.url as string | undefined;
                      return (
                        <li key={i}>
                          <span className="mono">{e.source}</span> · {e.kind} —{" "}
                          {url ? (
                            <a
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ color: "var(--accent)", textDecoration: "none", fontWeight: 500 }}
                            >
                              {e.summary}
                            </a>
                          ) : (
                            e.summary
                          )}{" "}
                          (<strong>{Number(e.severity).toFixed(2)}</strong>)
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <div className="empty-state">No normalized evidence returned in this run.</div>
                )}
              </div>
              <div>
                <h2>Raw evidence</h2>
                {Object.entries(result.raw_evidence_by_connector ?? {}).map(([name, payload]) => (
                  <details key={name} className="accordion" open={name === "github"}>
                    <summary>{name}</summary>
                    <pre>{JSON.stringify(payload, null, 2)}</pre>
                  </details>
                ))}
              </div>
            </div>
          ) : null}
          {activeResultTab === "agents" ? (
            <>
              <h2>Agent opinions</h2>
              {result.agent_opinions?.length ? (
                <ul className="list-plain agent-opinions-list">
                  {result.agent_opinions.map((o, i) => (
                    <AgentOpinionCard key={`${o.agent_id}-${i}`} opinion={o} />
                  ))}
                </ul>
              ) : (
                <div className="empty-state">No agent opinions available for this run.</div>
              )}
            </>
          ) : null}
          {activeResultTab === "explainability" ? (
            <>
              <h2>Full explanation</h2>
              <div className="explanation">
                <ReactMarkdown>{result.explanation ?? ""}</ReactMarkdown>
              </div>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
