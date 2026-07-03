import { Link } from "react-router-dom";
import { PROVIDERS, type AIProvidersTabProps } from "./types";

export function AIProvidersTab({
  canEdit,
  saving,
  defaultProvider,
  setDefaultProvider,
  providerDraft,
  setProviderDraft,
  providerStatus,
  aiTestPrompt,
  setAiTestPrompt,
  onSave,
  onValidate,
  onRuntimeCheck,
}: AIProvidersTabProps) {
  return (
    <div className="card">
      <div className="workspace-section-intro">
        <div>
          <h2>AI providers</h2>
          <p>Pick a default provider, add keys, test connection, and save.</p>
          <p className="field-hint" style={{ marginTop: "0.5rem" }}>
            Browse the canonical <Link to="/app/tool-registry">AgileOps tool registry</Link> for shipped tools, API endpoints, and PM scenarios.
          </p>
        </div>
        <div className="workspace-meta">Keep advanced settings collapsed unless needed</div>
      </div>
      <div className="form-row">
        <label htmlFor="default-provider-ai" className="field-label-required">
          Default provider
        </label>
        <select
          id="default-provider-ai"
          value={defaultProvider}
          onChange={(e) => setDefaultProvider(e.target.value)}
          disabled={!canEdit || saving}
        >
          <option value="">None</option>
          {PROVIDERS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>
      {PROVIDERS.map((name) => {
        const draft = providerDraft[name];
        const status = providerStatus(name);
        if (!draft) return null;
        return (
          <div key={name} className="config-block">
            <div className="settings-connector-head">
              <h3 className="settings-connector-title">{name}</h3>
              <label className="settings-enable-inline">
                <input
                  type="checkbox"
                  checked={draft.enabled}
                  onChange={(e) =>
                    setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], enabled: e.target.checked } }))
                  }
                  disabled={!canEdit || saving}
                />{" "}
                Enabled
              </label>
            </div>

            <div className="config-columns">
              <div className="form-row">
                <label className="field-label-required">Model</label>
                <input
                  value={draft.model_name}
                  onChange={(e) =>
                    setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], model_name: e.target.value } }))
                  }
                  disabled={!canEdit || saving}
                />
              </div>
              <div className="form-row">
                <label>Endpoint URL</label>
                <input
                  value={draft.endpoint_url}
                  onChange={(e) =>
                    setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], endpoint_url: e.target.value } }))
                  }
                  disabled={!canEdit || saving}
                />
              </div>
              <div className="form-row">
                <label>Key reference (optional)</label>
                <input
                  value={draft.api_key_ref}
                  onChange={(e) =>
                    setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], api_key_ref: e.target.value } }))
                  }
                  placeholder={status?.api_key_ref ?? "e.g. secret://tenant/openai"}
                  disabled={!canEdit || saving}
                />
              </div>
              <div className="form-row">
                <label className={name === "ollama" ? "" : "field-label-required"}>API key {name === "ollama" && "(optional)"}</label>
                <input
                  type="password"
                  value={draft.api_key}
                  onChange={(e) =>
                    setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], api_key: e.target.value } }))
                  }
                  disabled={!canEdit || saving}
                />
              </div>
            </div>
            <details style={{ marginTop: "0.35rem" }}>
              <summary style={{ cursor: "pointer", color: "var(--muted)" }}>Advanced settings</summary>
              <div className="config-columns" style={{ marginTop: "0.55rem" }}>
                <div className="form-row">
                  <label>Temperature</label>
                  <input
                    value={draft.temperature}
                    onChange={(e) =>
                      setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], temperature: e.target.value } }))
                    }
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Max tokens</label>
                  <input
                    value={draft.max_tokens}
                    onChange={(e) =>
                      setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], max_tokens: e.target.value } }))
                    }
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Timeout seconds</label>
                  <input
                    value={draft.timeout_seconds}
                    onChange={(e) =>
                      setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], timeout_seconds: e.target.value } }))
                    }
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Retry count</label>
                  <input
                    value={draft.retry_count}
                    onChange={(e) =>
                      setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], retry_count: e.target.value } }))
                    }
                    disabled={!canEdit || saving}
                  />
                </div>
              </div>
            </details>
            <div className="actions">
              <span className={`status-chip ${status?.enabled ? "succeeded" : "queued"}`}>
                {status?.enabled ? "configured" : "not configured"}
              </span>
              <button className="btn btn-ghost" type="button" onClick={() => onValidate(name)} disabled={!canEdit || saving}>
                Test connection
              </button>
              <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
                {status?.last_validation_ok == null
                  ? "Not validated"
                  : status.last_validation_ok
                    ? "Validation passed"
                    : status.last_validation_error || "Validation failed"}
              </span>
            </div>
          </div>
        );
      })}
      <div className="config-block">
        <h3>Runtime check</h3>
        <div className="form-row">
          <label>Test prompt</label>
          <textarea value={aiTestPrompt} onChange={(e) => setAiTestPrompt(e.target.value)} disabled={!canEdit || saving} />
        </div>
        <div className="actions">
          <button className="btn btn-ghost" type="button" onClick={onRuntimeCheck} disabled={!canEdit || saving}>
            Run runtime check
          </button>
        </div>
      </div>
      <button className="btn btn-primary" type="button" disabled={!canEdit || saving} onClick={onSave}>
        {saving ? "Saving…" : "Save AI provider settings"}
      </button>
    </div>
  );
}
