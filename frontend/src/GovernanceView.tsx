import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { GovernanceRunResult, PromptLibrary, TenantRow, UserPublic } from "./api";

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

  const pmView = result?.pm_view as Record<string, unknown> | undefined;
  const consensus = result?.consensus as Record<string, number> | undefined;
  const rar = result?.rar as Record<string, unknown> | undefined;
  const utility = result?.utility as Record<string, unknown> | undefined;
  const xi = (result?.explainability as Record<string, unknown> | undefined)?.xi_score as number | undefined;

  const consensusScore = consensus?.consensus_score ?? null;

  const scoreClass = useMemo(() => {
    if (consensusScore == null) return "";
    if (consensusScore >= 0.65) return "good";
    if (consensusScore >= 0.45) return "warn";
    return "bad";
  }, [consensusScore]);
  const [activeResultTab, setActiveResultTab] = useState<"executive" | "evidence" | "agents" | "explainability">(
    "executive"
  );

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
        <div className="workspace-card-title">
          <h2>Compose request</h2>
        </div>
        <p className="workspace-card-subtitle">Select a prompt template or write a custom governance question.</p>
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
          <label htmlFor="prompt">Question</label>
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
          <h2>Decision snapshot</h2>
          <p className="workspace-card-subtitle">Live result posture from the latest governance execution.</p>
          <div className="metrics">
            <div className="metric">
              <div className="label">Consensus</div>
              <div className={`value ${scoreClass}`}>{consensusScore != null ? consensusScore.toFixed(2) : "—"}</div>
            </div>
            <div className="metric">
              <div className="label">RAR</div>
              <div className="value">{rar?.rar_triggered ? `Yes (${rar.rar_loops})` : "No"}</div>
            </div>
            <div className="metric">
              <div className="label">Action</div>
              <div className="value mono" style={{ fontSize: "0.85rem" }}>
                {String(utility?.recommended_action ?? "—")}
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
          <h2>Batch results</h2>
          <pre className="mono" style={{ fontSize: "0.8rem", overflow: "auto" }}>
            {JSON.stringify(batchResult, null, 2)}
          </pre>
        </div>
      ) : null}

      {result ? (
        <>
          <div className="card">
            <div className="workspace-toolbar">
              <button className={`btn btn-ghost btn-sm ${activeResultTab === "executive" ? "active" : ""}`} type="button" onClick={() => setActiveResultTab("executive")}>Executive</button>
              <button className={`btn btn-ghost btn-sm ${activeResultTab === "evidence" ? "active" : ""}`} type="button" onClick={() => setActiveResultTab("evidence")}>Evidence</button>
              <button className={`btn btn-ghost btn-sm ${activeResultTab === "agents" ? "active" : ""}`} type="button" onClick={() => setActiveResultTab("agents")}>Agents</button>
              <button className={`btn btn-ghost btn-sm ${activeResultTab === "explainability" ? "active" : ""}`} type="button" onClick={() => setActiveResultTab("explainability")}>Explainability</button>
            </div>
            {activeResultTab === "executive" ? (
              <>
                <h2>Executive view</h2>
                {pmView ? (
                  <>
                    <p style={{ margin: "0 0 0.5rem", fontWeight: 600 }}>{String(pmView.title ?? "")}</p>
                    <div className="pm-summary">
                      <ReactMarkdown>{String(pmView.summary_markdown ?? "")}</ReactMarkdown>
                    </div>
                  </>
                ) : null}
                <p className="field-hint">Connectors: {(result.connectors_used as string[] | undefined)?.join(", ") || "—"}</p>
              </>
            ) : null}
            {activeResultTab === "evidence" ? (
              <div className="workspace-split">
                <div>
                  <h2>Normalized evidence</h2>
                  <ul className="list-plain">
                    {((result.normalized_evidence as Record<string, unknown>[]) ?? []).map((e, i) => (
                      <li key={i}>
                        <span className="mono">{String(e.source)}</span> · {String(e.kind)} — {String(e.summary)} (
                        <strong>{Number(e.severity).toFixed(2)}</strong>)
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h2>Raw evidence</h2>
                  {Object.entries((result.raw_evidence_by_connector as Record<string, unknown>) ?? {}).map(([name, payload]) => (
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
                <ul className="list-plain">
                  {((result.agent_opinions as Record<string, unknown>[]) ?? []).map((o, i) => (
                    <li key={i}>
                      <strong>{String(o.agent_id)}</strong> ({String(o.risk_theme)}, conf {Number(o.confidence).toFixed(2)}):{" "}
                      {String(o.claim)}
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
            {activeResultTab === "explainability" ? (
              <>
                <h2>Full explanation</h2>
                <div className="explanation">
                  <ReactMarkdown>{String(result.explanation ?? "")}</ReactMarkdown>
                </div>
              </>
            ) : null}
            </div>
        </>
      ) : null}
    </div>
  );
}
