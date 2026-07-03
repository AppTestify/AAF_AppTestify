import { useMemo, useState, useEffect, useRef } from "react";
import { Link, useSearchParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import type {
  AgentOpinion,
  GovernanceRunResult,
  PromptLibrary,
  ConnectorConfig,
  TenantRow,
  UserPublic,
  UtilityResult,
} from "./api";
import { askAssistant, formatAgentLabel, exportRunBriefPdf, fetchConnectorConfigs } from "./api";
import { GuardrailStatusPanel } from "./components/governance/GuardrailStatusPanel";
import { deriveAskColumns } from "./lib/governancePresentation";
import { EvidenceDetailCell, linkifyEvidenceText } from "./lib/evidenceLinks";

function ensureArray(val: unknown): string[] {
  if (Array.isArray(val)) return val.map(String);
  if (typeof val === "string" && val.trim() !== "") return [val];
  return [];
}


function ScopeListSelector({
  title, items, selectedItems, searchQuery, debouncedQuery, onSearchChange, onToggleItem, onToggleAll,
}: {
  title: string; items: string[]; selectedItems: string[]; searchQuery: string; debouncedQuery: string;
  onSearchChange: (q: string) => void; onToggleItem: (item: string) => void; onToggleAll: (filteredItems: string[], select: boolean) => void;
}) {
  const filtered = useMemo(() => {
    const q = debouncedQuery.toLowerCase();
    return items.filter(i => i.toLowerCase().includes(q));
  }, [items, debouncedQuery]);
  
  const allSelected = filtered.length > 0 && filtered.every(i => selectedItems.includes(i));
  const someSelected = filtered.some(i => selectedItems.includes(i));
  const indeterminate = someSelected && !allSelected;
  
  return (
    <div style={{ marginBottom: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
        <h4 style={{ margin: 0, fontSize: "0.95rem", color: "var(--text)", fontWeight: 600 }}>{title}</h4>
        {filtered.length > 0 && (
          <label style={{ fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer", color: "var(--accent)", fontWeight: 500 }}>
            <input
              type="checkbox"
              checked={allSelected}
              ref={el => { if (el) el.indeterminate = indeterminate; }}
              onChange={(e) => onToggleAll(filtered, e.target.checked)}
            />
            Select all
          </label>
        )}
      </div>

      <div style={{ position: "relative", marginBottom: "1rem" }}>
        <span style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "var(--muted)", fontSize: "0.9rem" }}>🔍</span>
        <input
          type="text"
          placeholder={`Search ${title.toLowerCase()}...`}
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          style={{ width: "100%", padding: "0.5rem 0.5rem 0.5rem 2.2rem", borderRadius: "6px", border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text)" }}
        />
      </div>

      {filtered.length > 0 ? (
        <>
          <div style={{ border: "1px solid var(--border)", borderRadius: "6px", overflow: "hidden" }}>
            <div style={{ display: "flex", flexDirection: "column", maxHeight: "250px", overflowY: "auto" }}>
              {filtered.map((item, idx) => (
                <label key={item} style={{ 
                  fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "0.75rem", cursor: "pointer", 
                  color: "var(--text)", padding: "0.75rem 1rem",
                  borderBottom: idx < filtered.length - 1 ? "1px solid var(--border)" : "none",
                  background: selectedItems.includes(item) ? "var(--surface2)" : "var(--surface)",
                  margin: 0
                }}>
                  <input type="checkbox" checked={selectedItems.includes(item)} onChange={() => onToggleItem(item)} />
                  <span style={{ color: "var(--muted)" }}>{title.toLowerCase().includes('branch') ? "🔀" : (title.toLowerCase().includes('repo') || title.toLowerCase().includes('project') ? "📁" : "📊")}</span>
                  <span style={{ fontWeight: 500 }}>{item}</span>
                </label>
              ))}
            </div>
          </div>
          <div style={{ fontSize: "0.85rem", color: "var(--muted)", marginTop: "0.5rem" }}>
            {selectedItems.length} of {items.length} {title.toLowerCase()} selected.
          </div>
        </>
      ) : (
        <div style={{ fontSize: "0.85rem", color: "var(--muted)", padding: "1.5rem", textAlign: "center", fontStyle: "italic", border: "1px dashed var(--border)", borderRadius: "6px" }}>
          No {title.toLowerCase()} match '{searchQuery}'
        </div>
      )}
    </div>
  );
}

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
  onRunGovernance: (runScope?: Record<string, any>) => void | Promise<void>;
  onBatch: () => void | Promise<void>;
  loading: boolean;
  runProgress: number;
  result: GovernanceRunResult | null;
  batchResult: unknown;
};

function AgentOpinionCard({ opinion }: { opinion: AgentOpinion }) {
  const evidence = opinion.evidence ?? [];
  const hasSignals = opinion.raw_signals && Object.keys(opinion.raw_signals).length > 0;

  return (
    <li className="agent-opinion-card">
      <div className="agent-opinion-head">
        <strong>{formatAgentLabel(opinion.agent_id, opinion.display_id)}</strong>
        <span className="status-chip running">{opinion.risk_theme.replace(/_/g, " ")}</span>
        <span className="field-hint">confidence {opinion.confidence.toFixed(2)}</span>
      </div>
      <p style={{ margin: "0.35rem 0 0.5rem" }}>{opinion.claim}</p>
      {evidence.length > 0 ? (
        <ul className="list-plain agent-evidence-list">
          {evidence.map((line, idx) => (
            <li key={idx}>{linkifyEvidenceText(line)}</li>
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
    runProgress,
    result,
    batchResult,
  } = props;

  const [searchParams] = useSearchParams();
  const contextualRunId = Number(searchParams.get("run_id") || 0);

  const utility: UtilityResult | undefined = result?.utility;
  const xi = result?.explainability?.xi_score;
  const framing = result?.decision_framing as
    | {
        orchestration?: { consensus_score?: number };
        findings_synthesis?: { consensus_score?: number; confidence?: number };
        primary_recommendation_source?: string;
      }
    | undefined;

  const orchConsensus = framing?.orchestration?.consensus_score ?? result?.consensus?.consensus_score ?? null;
  const scoreClass = useMemo(() => {
    const v = orchConsensus;
    if (v == null) return "";
    if (v >= 0.65) return "good";
    if (v >= 0.45) return "warn";
    return "bad";
  }, [orchConsensus]);

  const [connectorConfigs, setConnectorConfigs] = useState<ConnectorConfig[]>([]);
  const [runScope, setRunScope] = useState<Record<string, string[]>>({});

  useEffect(() => {
    fetchConnectorConfigs().then(configs => {
      setConnectorConfigs(configs);
      const initialScope: Record<string, string[]> = {};
      configs.forEach(c => {
         if (c.connector_name === "github" && c.config_json) {
           initialScope["github_repos"] = ensureArray(c.config_json.repos);
           initialScope["github_branches"] = ensureArray(c.config_json.release_branches);
         }
         if (c.connector_name === "jira" && c.config_json) {
           initialScope["jira_projects"] = ensureArray(c.config_json.projects);
           initialScope["jira_boards"] = ensureArray(c.config_json.board_ids);
         }
         if (c.connector_name === "gitlab" && c.config_json) {
           initialScope["gitlab_projects"] = ensureArray(c.config_json.project_ids);
           initialScope["gitlab_branches"] = ensureArray(c.config_json.release_branches);
         }
         if (c.connector_name === "finops" && c.config_json) {
           initialScope["finops_providers"] = ensureArray(c.config_json.providers);
           initialScope["finops_profiles"] = ensureArray(c.config_json.cost_file_paths);
         }
      });
      setRunScope(initialScope);
    }).catch(console.error);
  }, []);

  const toggleScopeItem = (key: string, val: string) => {
    setRunScope(prev => {
      const current = prev[key] || [];
      if (current.includes(val)) return { ...prev, [key]: current.filter(x => x !== val) };
      return { ...prev, [key]: [...current, val] };
    });
  };

  const setAllScopeItems = (key: string, values: string[], select: boolean) => {
    setRunScope(prev => ({ ...prev, [key]: select ? values : [] }));
  };
  const [activeResultTab, setActiveResultTab] = useState<
    "executive" | "evidence" | "agents" | "explainability" | "integrity"
  >("executive");
    const [showScopeModal, setShowScopeModal] = useState(false);
  const [activeScopeTab, setActiveScopeTab] = useState<string>("github");

  const [searchQueries, setSearchQueries] = useState<Record<string, string>>({});
  const [debouncedQueries, setDebouncedQueries] = useState<Record<string, string>>({});

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQueries(searchQueries), 200);
    return () => clearTimeout(timer);
  }, [searchQueries]);

  const runDisabledReason = !prompt.trim() ? "Please enter a prompt to continue" : "";


  const [showAdmin, setShowAdmin] = useState(false);
  const [followUp, setFollowUp] = useState("");
  const [chatHistory, setChatHistory] = useState<{ role: "user" | "assistant"; text: string; confidence?: number; evidence?: Record<string, unknown> }[]>(
    []
  );
  const [chatLoading, setChatLoading] = useState(false);
  const chatHistoryRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTo({
        top: chatHistoryRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [chatHistory]);

  const suggestedPrompts = [
    "What is our current release risk?",
    "Are there latency or error rate concerns?",
    "Any cost spikes I should know about?",
  ];

  const sendFollowUp = async (question: string) => {
    const q = question.trim();
    if (!q) return;
    setChatLoading(true);
    setChatHistory((h) => [...h, { role: "user", text: q }]);
    try {
      const historyPayload = chatHistory.map(m => ({ role: m.role, text: m.text }));
      const res = await askAssistant(q, historyPayload);
      setChatHistory((h) => [...h, { role: "assistant", text: res.answer, confidence: res.confidence, evidence: res.evidence }]);
    } catch (err) {
      setChatHistory((h) => [
        ...h,
        { role: "assistant", text: err instanceof Error ? err.message : "Assistant unavailable" },
      ]);
    } finally {
      setChatLoading(false);
      setFollowUp("");
    }
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportPdf = async () => {
    if (!result?.run_id) return;
    try {
      const blob = await exportRunBriefPdf(result.run_id);
      downloadBlob(blob, `governance_run_${result.run_id}.pdf`);
    } catch (err) {
      console.error("Failed to export PDF", err);
    }
  };

  const askColumns = result ? deriveAskColumns(result) : null;
  const formatIndex = (v: number | undefined) => (v != null && !Number.isNaN(v) ? v.toFixed(2) : "—");

  return (
    <div className="app">
      <header className="gov-hub-header">
        <p className="gov-hub-eyebrow">AI Assistant</p>
        <h1 className="gov-hub-title">Ask Casantris AI</h1>
        <p className="gov-hub-lead">
          Governance recommendations grounded in real evidence and traceable reasoning — not generic chat.
        </p>
      </header>

      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}

      {contextualRunId > 0 ? (
        <div className="alert alert-info" role="status">
          Viewing run #{contextualRunId}.{" "}
          <Link to={`/app/runs?run_id=${contextualRunId}`}>Open run detail</Link>
        </div>
      ) : null}

      <article className="gov-ask-card gov-chat-panel">
        <p className="gov-hub-eyebrow">Follow-up chat</p>
        <div className="gov-suggested-prompts">
          {suggestedPrompts.map((p) => (
            <button key={p} type="button" className="gov-search-chip" onClick={() => void sendFollowUp(p)}>
              {p}
            </button>
          ))}
        </div>
        {chatHistory.length ? (
          <ul ref={chatHistoryRef} className="gov-chat-history">
            {chatHistory.map((m, i) => (
              <li key={i} className={m.role === "user" ? "gov-chat-user" : "gov-chat-assistant"}>
                <strong>{m.role === "user" ? "You" : "Casantris"}</strong>
                <p>{m.text}</p>
                {m.confidence != null ? <span className="field-hint">confidence {m.confidence.toFixed(2)}</span> : null}
                {m.evidence && Object.keys(m.evidence).length > 0 ? (
                  <div className="gov-chat-citations" style={{ marginTop: "0.5rem" }}>
                    <p style={{ fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 600, color: "var(--muted)", margin: "0 0 0.25rem" }}>Cited Evidence</p>
                    {Object.entries(m.evidence).map(([key, val]) => (
                      <details key={key} className="accordion" style={{ fontSize: "0.8rem", marginBottom: "0.25rem" }}>
                        <summary style={{ padding: "0.25rem 0.5rem" }}>Source: {key}</summary>
                        <pre style={{ margin: 0, padding: "0.5rem", fontSize: "0.75rem", maxHeight: "150px", overflow: "auto" }}>
                          {JSON.stringify(val, null, 2)}
                        </pre>
                      </details>
                    ))}
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
        <div className="gov-ask-toolbar">
          <input
            type="text"
            value={followUp}
            onChange={(e) => setFollowUp(e.target.value)}
            placeholder="Ask a follow-up about this governance context…"
            style={{ flex: 1, minWidth: "200px", padding: "0.5rem", borderRadius: "6px", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text)" }}
            onKeyDown={(e) => {
              if (e.key === "Enter") void sendFollowUp(followUp);
            }}
          />
          <button className="btn btn-ghost btn-sm" type="button" disabled={chatLoading} onClick={() => void sendFollowUp(followUp)}>
            {chatLoading ? "Thinking…" : "Ask"}
          </button>
        </div>
      </article>

      <article className="gov-ask-card">
        <p className="gov-hub-eyebrow" style={{ marginBottom: "0.5rem" }}>
          Governance Question
        </p>
        <div className="form-row">
          <label htmlFor="library">Prompt library</label>
          <select
            id="library"
            value={promptId ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              if (v) applyLibraryPrompt(v);
              else setPromptId(null);
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
            placeholder="Can we release today, or are GitHub issues, Jira blockers, and cloud cost spikes creating delivery risk?"
          />
        </div>
        <div className="gov-ask-toolbar">
          {result ? (
            <Link to="/app/evidence" className="btn btn-ghost btn-sm">
              View Evidence
            </Link>
          ) : (
            <button type="button" className="btn btn-ghost btn-sm" disabled aria-disabled="true">
              View Evidence
            </button>
          )}
          <Link to="/app/reports" className="btn btn-ghost btn-sm">
            Export Summary
          </Link>
          {result?.run_id ? (
            <button type="button" className="btn btn-ghost btn-sm" onClick={handleExportPdf}>
              Export Brief (PDF)
            </button>
          ) : null}
          <div className="gov-ask-toolbar" style={{ display: "flex", gap: "1rem", marginTop: "1rem", justifyContent: "flex-end" }}>
            <button
              className="btn btn-secondary"
              type="button"
              onClick={() => setShowScopeModal(true)}
            >
              Configure Scope
            </button>
            <button
              className="btn btn-primary"
              type="button"
              disabled={loading || !prompt.trim()}
              title={runDisabledReason}
              onClick={() => onRunGovernance(runScope)}
            >
              Run Governance Check
            </button>
          </div>
        </div>
        {loading ? (
          <div className="gov-progress-container" style={{ marginTop: "1rem" }}>
            <div className="gov-progress-bar" style={{ height: "6px", background: "var(--border)", borderRadius: "4px", overflow: "hidden" }}>
              <div style={{ height: "100%", background: "linear-gradient(90deg, #3b82f6, #8b5cf6)", width: `${Math.round(runProgress)}%`, transition: "width 0.5s ease-out" }} />
            </div>
            <span className="gov-progress-text" style={{ display: "block", marginTop: "0.5rem", fontSize: "0.85rem", color: "var(--muted)" }}>
              {Math.round(runProgress)}% - Synthesizing signals...
            </span>
          </div>
        ) : null}
      </article>
      {showScopeModal && (
        <div style={{
          position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh",
          background: "rgba(0,0,0,0.3)", zIndex: 9999,
          display: "flex", justifyContent: "center", alignItems: "center"
        }}>
          <div style={{
            background: "var(--surface)", borderRadius: "12px",
            width: "550px", maxWidth: "90vw", maxHeight: "90vh",
            boxShadow: "0 10px 30px rgba(0,0,0,0.2)", display: "flex", flexDirection: "column"
          }}>
            {/* Header */}
            <div style={{ padding: "1.5rem", borderBottom: "1px solid var(--border)", position: "relative" }}>
              <button onClick={() => setShowScopeModal(false)} style={{
                position: "absolute", top: "1.5rem", right: "1.5rem",
                background: "none", border: "none", fontSize: "1.2rem", cursor: "pointer", color: "var(--muted)"
              }}>✕</button>
              <h3 style={{ margin: "0 0 1rem 0" }}>Configure run scope<div style={{ fontSize: "0.85rem", color: "var(--muted)", fontWeight: 400, marginTop: "0.25rem" }}>Choose what Casantris AI should analyze.</div></h3>
              
              {connectorConfigs.filter(c => c.enabled).length > 0 && (
                <div style={{ display: "flex", overflowX: "auto", gap: "1rem" }}>
                  {connectorConfigs.filter(c => c.enabled).map(c => (
                    <button
                      key={c.connector_name}
                      type="button"
                      onClick={() => setActiveScopeTab(c.connector_name)}
                      style={{
                        padding: "0 0 0.5rem 0", background: "none", border: "none",
                        borderBottom: activeScopeTab === c.connector_name ? "2px solid var(--accent)" : "2px solid transparent",
                        color: activeScopeTab === c.connector_name ? "var(--accent)" : "var(--muted)",
                        cursor: "pointer", fontWeight: activeScopeTab === c.connector_name ? 600 : 400,
                        whiteSpace: "nowrap"
                      }}
                    >
                      {c.connector_name.charAt(0).toUpperCase() + c.connector_name.slice(1)}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Scrollable Content */}
            <div style={{ padding: "1.5rem", overflowY: "auto", flex: 1 }}>
              {connectorConfigs.filter(c => c.enabled).length === 0 ? (
                <div style={{ fontSize: "0.85rem", color: "var(--muted)", textAlign: "center", padding: "1rem 0" }}>
                  No active integrations found.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column" }}>
                  {connectorConfigs.filter(c => c.enabled && c.connector_name === activeScopeTab).map(c => {
                    const name = c.connector_name;
                    if (name === "github") {
                      return (
                        <div key="github">
                          <ScopeListSelector title="Repositories" items={ensureArray(c.config_json?.repos)} selectedItems={runScope["github_repos"] || []} searchQuery={searchQueries["github_repos"] || ""} debouncedQuery={debouncedQueries["github_repos"] || ""} onSearchChange={(q) => setSearchQueries(p => ({...p, github_repos: q}))} onToggleItem={(i) => toggleScopeItem("github_repos", i)} onToggleAll={(items, sel) => setAllScopeItems("github_repos", items, sel)} />
                          <ScopeListSelector title="Release Branches" items={ensureArray(c.config_json?.release_branches)} selectedItems={runScope["github_branches"] || []} searchQuery={searchQueries["github_branches"] || ""} debouncedQuery={debouncedQueries["github_branches"] || ""} onSearchChange={(q) => setSearchQueries(p => ({...p, github_branches: q}))} onToggleItem={(i) => toggleScopeItem("github_branches", i)} onToggleAll={(items, sel) => setAllScopeItems("github_branches", items, sel)} />
                        </div>
                      );
                    }
                    if (name === "jira") {
                      return (
                        <div key="jira">
                          <ScopeListSelector title="Projects" items={ensureArray(c.config_json?.projects)} selectedItems={runScope["jira_projects"] || []} searchQuery={searchQueries["jira_projects"] || ""} debouncedQuery={debouncedQueries["jira_projects"] || ""} onSearchChange={(q) => setSearchQueries(p => ({...p, jira_projects: q}))} onToggleItem={(i) => toggleScopeItem("jira_projects", i)} onToggleAll={(items, sel) => setAllScopeItems("jira_projects", items, sel)} />
                          <ScopeListSelector title="Boards" items={ensureArray(c.config_json?.board_ids)} selectedItems={runScope["jira_boards"] || []} searchQuery={searchQueries["jira_boards"] || ""} debouncedQuery={debouncedQueries["jira_boards"] || ""} onSearchChange={(q) => setSearchQueries(p => ({...p, jira_boards: q}))} onToggleItem={(i) => toggleScopeItem("jira_boards", i)} onToggleAll={(items, sel) => setAllScopeItems("jira_boards", items, sel)} />
                        </div>
                      );
                    }
                    if (name === "gitlab") {
                      return (
                        <div key="gitlab">
                          <ScopeListSelector title="Projects" items={ensureArray(c.config_json?.project_ids)} selectedItems={runScope["gitlab_projects"] || []} searchQuery={searchQueries["gitlab_projects"] || ""} debouncedQuery={debouncedQueries["gitlab_projects"] || ""} onSearchChange={(q) => setSearchQueries(p => ({...p, gitlab_projects: q}))} onToggleItem={(i) => toggleScopeItem("gitlab_projects", i)} onToggleAll={(items, sel) => setAllScopeItems("gitlab_projects", items, sel)} />
                          <ScopeListSelector title="Release Branches" items={ensureArray(c.config_json?.release_branches)} selectedItems={runScope["gitlab_branches"] || []} searchQuery={searchQueries["gitlab_branches"] || ""} debouncedQuery={debouncedQueries["gitlab_branches"] || ""} onSearchChange={(q) => setSearchQueries(p => ({...p, gitlab_branches: q}))} onToggleItem={(i) => toggleScopeItem("gitlab_branches", i)} onToggleAll={(items, sel) => setAllScopeItems("gitlab_branches", items, sel)} />
                        </div>
                      );
                    }
                    if (name === "finops") {
                      return (
                        <div key="finops">
                          <ScopeListSelector title="Cloud Providers" items={ensureArray(c.config_json?.providers)} selectedItems={runScope["finops_providers"] || []} searchQuery={searchQueries["finops_providers"] || ""} debouncedQuery={debouncedQueries["finops_providers"] || ""} onSearchChange={(q) => setSearchQueries(p => ({...p, finops_providers: q}))} onToggleItem={(i) => toggleScopeItem("finops_providers", i)} onToggleAll={(items, sel) => setAllScopeItems("finops_providers", items, sel)} />
                          <ScopeListSelector title="Billing Profiles" items={ensureArray(c.config_json?.cost_file_paths)} selectedItems={runScope["finops_profiles"] || []} searchQuery={searchQueries["finops_profiles"] || ""} debouncedQuery={debouncedQueries["finops_profiles"] || ""} onSearchChange={(q) => setSearchQueries(p => ({...p, finops_profiles: q}))} onToggleItem={(i) => toggleScopeItem("finops_profiles", i)} onToggleAll={(items, sel) => setAllScopeItems("finops_profiles", items, sel)} />
                        </div>
                      );
                    }
                    return null;
                  })}
                </div>
              )}
            </div>

            
          </div>
        </div>
      )}


      {result && askColumns ? (
        <article className="gov-ask-output">
          <div className="workspace-section-intro">
            <div>
              <p className="gov-hub-eyebrow">Output</p>
              <h2 style={{ margin: 0 }}>Governance Recommendation</h2>
            </div>
            <div className="gov-ask-risk-pills">
              <span className="gov-pill gov-pill--high">Delivery Risk: {askColumns.deliveryRisk}</span>
              <span className="gov-pill gov-pill--medium">Cost Risk: {askColumns.costRisk}</span>
              <span className="gov-pill gov-pill--medium">Security: {askColumns.securityRisk}</span>
              <span className="gov-pill gov-pill--healthy">Confidence: {askColumns.confidence}</span>
            </div>
          </div>
          <p style={{ margin: "0.75rem 0", fontWeight: 600, fontSize: "1.05rem" }}>{askColumns.recommendation}</p>
          <div className="gov-ask-columns">
            <div>
              <h4>Why this matters</h4>
              <p>{askColumns.why}</p>
            </div>
            <div>
              <h4>Business impact</h4>
              <p>{askColumns.impact}</p>
            </div>
            <div>
              <h4>Suggested next step</h4>
              <p>{askColumns.nextStep}</p>
            </div>
          </div>
          <div className="gov-recommendation-actions" style={{ marginTop: "1rem" }}>
            <Link to="/app/runs" className="btn btn-ghost btn-sm">
              Agent Reasoning
            </Link>
            <Link to="/app/evidence" className="btn btn-ghost btn-sm">
              Evidence Hub
            </Link>
            <Link to="/app/cases" className="btn btn-primary btn-sm">
              Open Decision Case
            </Link>
          </div>
          <div className="metrics" style={{ marginTop: "1rem" }}>
            <div className="metric">
              <div className="label">Consensus</div>
              <div className={`value ${scoreClass}`}>{orchConsensus != null ? orchConsensus.toFixed(2) : "—"}</div>
            </div>
            <div className="metric">
              <div className="label">Global U</div>
              <div className="value">{formatIndex(utility?.global_utility)}</div>
            </div>
            <div className="metric">
              <div className="label">P / Ci / R</div>
              <div className="value mono" style={{ fontSize: "0.85rem" }}>
                {formatIndex(utility?.perf_index)} / {formatIndex(utility?.cost_index)} / {formatIndex(utility?.risk_index)}
              </div>
            </div>
            <div className="metric">
              <div className="label">XI</div>
              <div className="value">{xi != null ? xi.toFixed(2) : "—"}</div>
            </div>
          </div>
        </article>
      ) : null}

      {result ? (
        <div className="card">
          <div className="gov-tabs">
            {(["executive", "evidence", "agents", "explainability", "integrity"] as const).map((tab) => (
              <button
                key={tab}
                className={`btn btn-ghost btn-sm ${activeResultTab === tab ? "active" : ""}`}
                type="button"
                onClick={() => setActiveResultTab(tab)}
              >
                {tab === "integrity" ? "Run integrity" : tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
          {activeResultTab === "executive" ? (
            <>
              {result.pm_view ? (
                <>
                  <p style={{ margin: "0 0 0.5rem", fontWeight: 600 }}>{result.pm_view.title}</p>
                  <div className="pm-summary">
                    <ReactMarkdown>{result.pm_view.summary_markdown}</ReactMarkdown>
                  </div>
                </>
              ) : (
                <div className="explanation">
                  <ReactMarkdown>{result.explanation ?? ""}</ReactMarkdown>
                </div>
              )}
            </>
          ) : null}
          {activeResultTab === "evidence" ? (
            <div className="workspace-split">
              <div>
                <h2>Normalized evidence</h2>
                {result.normalized_evidence?.length ? (
                  <ul className="list-plain">
                    {result.normalized_evidence.map((e, i) => (
                      <li key={i}>
                        <span className="mono">{e.source}</span> · {e.kind} —{" "}
                        <EvidenceDetailCell detail={e.summary} record={e} />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="empty-state">No normalized evidence.</div>
                )}
              </div>
              <div>
                <h2>Raw evidence</h2>
                {Object.entries(result.raw_evidence_by_connector ?? {}).map(([name, payload]) => (
                  <details key={name} className="accordion">
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
                <div className="empty-state">No agent opinions.</div>
              )}
            </>
          ) : null}
          {activeResultTab === "explainability" ? (
            <div className="explanation">
              <ReactMarkdown>{result.explanation ?? ""}</ReactMarkdown>
            </div>
          ) : null}
          {activeResultTab === "integrity" ? (
            <GuardrailStatusPanel
              guardrails={result.guardrails}
              llmCost={result.llm_cost}
              llmBudget={result.llm_budget}
            />
          ) : null}
        </div>
      ) : null}

      {result?.guardrails?.enabled && activeResultTab !== "integrity" ? (
        <GuardrailStatusPanel
          guardrails={result.guardrails}
          llmCost={result.llm_cost}
          llmBudget={result.llm_budget}
          compact
        />
      ) : null}

      {batchResult ? (
        <div className="card">
          <h2>Batch results</h2>
          <pre className="mono" style={{ fontSize: "0.8rem", overflow: "auto" }}>
            {JSON.stringify(batchResult, null, 2)}
          </pre>
        </div>
      ) : null}

      {user.is_superadmin && tenants ? (
        <details className="card" open={showAdmin} onToggle={(e) => setShowAdmin(e.currentTarget.open)}>
          <summary style={{ cursor: "pointer", fontWeight: 600 }}>Superadmin — tenants & batch</summary>
          <ul className="list-plain" style={{ margin: "0.75rem 0" }}>
            {tenants.map((t) => (
              <li key={t.id}>
                <span className="mono">{t.slug}</span> — {t.name}
              </li>
            ))}
          </ul>
          <form onSubmit={onCreateTenant}>
            <div className="form-row">
              <label htmlFor="tname">New tenant name</label>
              <input id="tname" value={newTenantName} onChange={(e) => setNewTenantName(e.target.value)} />
            </div>
            <div className="form-row">
              <label htmlFor="tslug">Slug</label>
              <input id="tslug" className="mono" value={newTenantSlug} onChange={(e) => setNewTenantSlug(e.target.value)} />
            </div>
            <button className="btn btn-ghost" type="submit" disabled={loading}>
              Add tenant
            </button>
          </form>
          {user.is_admin ? (
            <button className="btn btn-ghost" type="button" disabled={loading} onClick={onBatch} style={{ marginTop: "0.5rem" }}>
              Run batch (library)
            </button>
          ) : null}
        </details>
      ) : null}
    </div>
  );
}
