import { PROVIDERS, type GeneralTabProps } from "./types";

export function GeneralTab({
  canEdit,
  saving,
  defaultProvider,
  setDefaultProvider,
  uiPrefsText,
  setUiPrefsText,
  llmKeysText,
  setLlmKeysText,
  ragConfigText,
  setRagConfigText,
  onSave,
}: GeneralTabProps) {
  return (
    <div className="settings-general-stack">
      <div className="card settings-highlight-card">
        <div className="workspace-section-intro">
          <div>
            <h2>General</h2>
            <p>Set your default AI route, then use Connectors and AI Providers to validate end-to-end.</p>
          </div>
        </div>
        <ol className="settings-onboarding-steps">
          <li>
            <strong>Default AI provider</strong> — picks which model family governance runs prefer.
          </li>
          <li>
            <strong>Connectors tab</strong> — link GitHub, GitLab, Jira, Azure DevOps; use <em>Save &amp; test</em> on each.
          </li>
          <li>
            <strong>AI Providers tab</strong> — add API keys and run <em>Test connection</em>.
          </li>
        </ol>
        <div className="config-columns settings-quick-grid">
          <div className="form-row">
            <label htmlFor="default-provider">Default AI provider</label>
            <select
              id="default-provider"
              value={defaultProvider}
              onChange={(e) => setDefaultProvider(e.target.value)}
              disabled={!canEdit || saving}
            >
              <option value="">None (not recommended for production)</option>
              {PROVIDERS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
            <p className="field-hint">Must match an enabled provider on the AI Providers tab.</p>
          </div>
        </div>
        <div className="actions settings-primary-actions">
          <button className="btn btn-primary" type="button" disabled={!canEdit || saving} onClick={onSave}>
            {saving ? "Saving…" : "Save general settings"}
          </button>
        </div>
      </div>

      <div className="card">
        <details className="settings-advanced-details">
          <summary>Advanced — JSON (UI preferences, LLM key map, RAG)</summary>
          <p className="workspace-meta" style={{ marginTop: "0.5rem" }}>
            For power users. Invalid JSON will fail on save. LLM keys: use real secret values only when updating; placeholder entries are ignored by the
            backend if unchanged. Optional keys: <code>team_capacity</code> (planned/available hours, leave_count),{" "}
            <code>mcp_enabled</code> + <code>mcp_servers</code> (github/atlassian stdio MCP brokers), <code>sast</code> (SonarCloud org/project_key/api_token).
          </p>
          <div className="form-row">
            <label htmlFor="ui-prefs">UI preferences (JSON)</label>
            <textarea
              id="ui-prefs"
              className="settings-json-area"
              value={uiPrefsText}
              onChange={(e) => setUiPrefsText(e.target.value)}
              disabled={!canEdit || saving}
              rows={8}
            />
          </div>
          <div className="form-row">
            <label htmlFor="llm-keys">LLM keys (JSON map)</label>
            <textarea
              id="llm-keys"
              className="settings-json-area"
              value={llmKeysText}
              onChange={(e) => setLlmKeysText(e.target.value)}
              disabled={!canEdit || saving}
              rows={8}
            />
          </div>
          <div className="form-row">
            <label htmlFor="rag-config">RAG config (JSON)</label>
            <textarea
              id="rag-config"
              className="settings-json-area"
              value={ragConfigText}
              onChange={(e) => setRagConfigText(e.target.value)}
              disabled={!canEdit || saving}
              rows={8}
            />
          </div>
          <button className="btn btn-ghost" type="button" disabled={!canEdit || saving} onClick={onSave}>
            Save advanced JSON
          </button>
        </details>
      </div>
    </div>
  );
}