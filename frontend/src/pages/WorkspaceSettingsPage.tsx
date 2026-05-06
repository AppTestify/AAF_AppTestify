import { useEffect, useMemo, useState } from "react";
import {
  fetchConnectorConfigs,
  fetchProviderConfigs,
  fetchTenantSettings,
  patchTenantSettings,
  runGovernance,
  saveConnectorConfigs,
  saveProviderConfigs,
  validateConnectorConfig,
  validateProviderConfig,
  type ConnectorConfig,
  type ProviderConfig,
  type TenantRow,
  type UserPublic,
} from "../api";

type SettingsTab = "general" | "connectors" | "ai";

type WorkspaceSettingsPageProps = {
  token: string;
  user: UserPublic;
  tenants: TenantRow[] | null;
  initialTab?: SettingsTab;
};

type ConnectorDraft = {
  enabled: boolean;
  config_json: Record<string, unknown>;
  credentials_json: Record<string, unknown>;
};

type ProviderDraft = {
  enabled: boolean;
  model_name: string;
  api_key: string;
  temperature: string;
  max_tokens: string;
  endpoint_url: string;
  api_key_ref: string;
  timeout_seconds: string;
  retry_count: string;
  metadata_json: Record<string, unknown>;
};

const PROVIDERS = ["openai", "anthropic", "azure_openai", "aws_bedrock"];
const CONNECTOR_HELP: Record<string, string> = {
  github: "Required when enabled: config_json.repo",
  jira: "Required when enabled: config_json.project",
  azure: "Required when enabled: config_json.subscription_id",
  aws: "Required when enabled: config_json.account_id",
  finops: "Required when enabled: config_json.cost_file",
};

export function WorkspaceSettingsPage({ token, user, tenants, initialTab = "general" }: WorkspaceSettingsPageProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);
  const [targetTenantSlug, setTargetTenantSlug] = useState<string | null>(user.tenant_slug ?? null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [defaultProvider, setDefaultProvider] = useState<string>("");
  const [uiPrefsText, setUiPrefsText] = useState<string>("{}");
  const [llmKeysText, setLlmKeysText] = useState<string>("{}");
  const [ragConfigText, setRagConfigText] = useState<string>("{}");
  const [connectorRows, setConnectorRows] = useState<ConnectorConfig[]>([]);
  const [connectorDraft, setConnectorDraft] = useState<Record<string, ConnectorDraft>>({});
  const [providerRows, setProviderRows] = useState<ProviderConfig[]>([]);
  const [providerDraft, setProviderDraft] = useState<Record<string, ProviderDraft>>({});
  const [aiTestPrompt, setAiTestPrompt] = useState("Health-check prompt: verify AI provider runtime configuration.");

  const canEdit = user.is_superadmin || user.is_admin;
  const targetForApi = user.is_superadmin ? targetTenantSlug : undefined;

  const tenantOptions = useMemo(() => {
    if (!user.is_superadmin || !tenants) return [];
    return tenants.map((t) => t.slug);
  }, [user.is_superadmin, tenants]);

  useEffect(() => {
    if (!user.is_superadmin) return;
    if (!targetTenantSlug && tenantOptions.length > 0) setTargetTenantSlug(tenantOptions[0]);
  }, [user.is_superadmin, tenantOptions, targetTenantSlug]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      fetchTenantSettings(token, targetForApi),
      fetchConnectorConfigs(token, targetForApi),
      fetchProviderConfigs(token, targetForApi),
    ])
      .then(([settings, connectors, providers]) => {
        setDefaultProvider(settings.default_ai_provider ?? "");
        setUiPrefsText(JSON.stringify(settings.ui_preferences ?? {}, null, 2));
        setLlmKeysText(
          JSON.stringify(
            (settings.llm_keys_configured || []).reduce((acc, k) => ({ ...acc, [k]: "<configured>" }), {}),
            null,
            2
          )
        );
        setRagConfigText(JSON.stringify(settings.rag_config_json ?? {}, null, 2));
        setConnectorRows(connectors);
        const cDraft: Record<string, ConnectorDraft> = {};
        connectors.forEach((c) => {
          cDraft[c.connector_name] = { enabled: c.enabled, config_json: c.config_json ?? {}, credentials_json: {} };
        });
        setConnectorDraft(cDraft);
        setProviderRows(providers.providers);
        const pDraft: Record<string, ProviderDraft> = {};
        providers.providers.forEach((p) => {
          pDraft[p.provider_name] = {
            enabled: p.enabled,
            model_name: p.model_name ?? "",
            api_key: "",
            temperature: p.temperature == null ? "" : String(p.temperature),
            max_tokens: p.max_tokens == null ? "" : String(p.max_tokens),
            endpoint_url: p.endpoint_url ?? "",
            api_key_ref: "",
            timeout_seconds: p.timeout_seconds == null ? "" : String(p.timeout_seconds),
            retry_count: p.retry_count == null ? "" : String(p.retry_count),
            metadata_json: p.metadata_json ?? {},
          };
        });
        PROVIDERS.forEach((name) => {
          if (!pDraft[name]) {
            pDraft[name] = {
              enabled: false,
              model_name: "",
              api_key: "",
              temperature: "",
              max_tokens: "",
              endpoint_url: "",
              api_key_ref: "",
              timeout_seconds: "",
              retry_count: "",
              metadata_json: {},
            };
          }
        });
        setProviderDraft(pDraft);
        if (!settings.default_ai_provider && providers.default_provider) {
          setDefaultProvider(providers.default_provider);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load settings"))
      .finally(() => setLoading(false));
  }, [token, targetForApi]);

  const handleSaveGeneral = async () => {
    try {
      setSaving(true);
      setMessage(null);
      const prefs = JSON.parse(uiPrefsText || "{}") as Record<string, unknown>;
      const llmKeys = JSON.parse(llmKeysText || "{}") as Record<string, string>;
      const ragConfig = JSON.parse(ragConfigText || "{}") as Record<string, unknown>;
      await patchTenantSettings(
        token,
        {
          default_ai_provider: defaultProvider || null,
          ui_preferences: prefs,
          llm_keys: llmKeys,
          rag_config_json: ragConfig,
        },
        targetForApi
      );
      setMessage("General settings saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save general settings");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveConnectors = async () => {
    try {
      setSaving(true);
      setMessage(null);
      const saved = await saveConnectorConfigs(token, connectorDraft, targetForApi);
      setConnectorRows(saved);
      setMessage("Connector settings saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save connectors");
    } finally {
      setSaving(false);
    }
  };

  const handleValidateConnector = async (name: string) => {
    try {
      setMessage(null);
      const validated = await validateConnectorConfig(token, name, targetForApi);
      setConnectorRows((prev) =>
        prev.map((c) => (c.connector_name === name ? validated : c)).concat(prev.some((c) => c.connector_name === name) ? [] : [validated])
      );
      setMessage(`${name} validated.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connector validation failed");
    }
  };

  const handleSaveProviders = async () => {
    try {
      setSaving(true);
      setMessage(null);
      const payload: Record<string, Record<string, unknown>> = {};
      Object.entries(providerDraft).forEach(([name, d]) => {
        payload[name] = {
          enabled: d.enabled,
          model_name: d.model_name || null,
          temperature: d.temperature === "" ? null : Number(d.temperature),
          max_tokens: d.max_tokens === "" ? null : Number(d.max_tokens),
          endpoint_url: d.endpoint_url || null,
          api_key_ref: d.api_key_ref || null,
          api_key: d.api_key || null,
          timeout_seconds: d.timeout_seconds === "" ? null : Number(d.timeout_seconds),
          retry_count: d.retry_count === "" ? null : Number(d.retry_count),
          metadata_json: d.metadata_json || {},
        };
      });
      const saved = await saveProviderConfigs(
        token,
        {
          default_provider: defaultProvider || null,
          providers: payload as Record<
            string,
            {
              enabled: boolean;
              model_name?: string | null;
              temperature?: number | null;
              max_tokens?: number | null;
              endpoint_url?: string | null;
              api_key_ref?: string | null;
              timeout_seconds?: number | null;
              retry_count?: number | null;
              metadata_json?: Record<string, unknown>;
            }
          >,
        },
        targetForApi
      );
      setProviderRows(saved.providers);
      setMessage("AI provider settings saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save AI providers");
    } finally {
      setSaving(false);
    }
  };

  const handleValidateProvider = async (provider: string) => {
    try {
      setMessage(null);
      const validated = await validateProviderConfig(token, provider, targetForApi);
      setProviderRows((prev) =>
        prev.map((p) => (p.provider_name === provider ? validated : p)).concat(prev.some((p) => p.provider_name === provider) ? [] : [validated])
      );
      setMessage(`${provider} connection test completed.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Provider validation failed");
    }
  };

  const handleAiRuntimeSmokeTest = async () => {
    try {
      setSaving(true);
      setMessage(null);
      const result = await runGovernance(token, aiTestPrompt, "ai-runtime-smoke", targetForApi);
      const runtime = (result.runtime_config as Record<string, unknown>) || {};
      const ai = (runtime.ai as Record<string, unknown>) || {};
      const activeProvider = ai.default_provider as string | undefined;
      setMessage(
        activeProvider
          ? `AI runtime smoke test succeeded. Active default provider: ${activeProvider}`
          : "AI runtime smoke test ran. No default provider configured."
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "AI runtime smoke test failed");
    } finally {
      setSaving(false);
    }
  };

  const connectorStatus = (name: string): ConnectorConfig | undefined =>
    connectorRows.find((c) => c.connector_name === name);
  const providerStatus = (name: string): ProviderConfig | undefined => providerRows.find((p) => p.provider_name === name);

  return (
    <div className="app">
      <header className="app-header workspace-page-head">
        <div className="brand">
          <h1>Settings</h1>
          <span>Tenant configuration, connectors, and AI providers</span>
        </div>
      </header>

      {user.is_superadmin && tenantOptions.length > 0 ? (
        <div className="card">
          <h2>Tenant scope</h2>
          <div className="form-row">
            <label htmlFor="tenant-scope">Manage tenant</label>
            <select
              id="tenant-scope"
              value={targetTenantSlug ?? ""}
              onChange={(e) => setTargetTenantSlug(e.target.value || null)}
            >
              {tenantOptions.map((slug) => (
                <option key={slug} value={slug}>
                  {slug}
                </option>
              ))}
            </select>
          </div>
        </div>
      ) : null}

      <div className="settings-tabs">
        <button className={activeTab === "general" ? "active" : ""} onClick={() => setActiveTab("general")} type="button">
          General
        </button>
        <button
          className={activeTab === "connectors" ? "active" : ""}
          onClick={() => setActiveTab("connectors")}
          type="button"
        >
          Connectors
        </button>
        <button className={activeTab === "ai" ? "active" : ""} onClick={() => setActiveTab("ai")} type="button">
          AI Providers
        </button>
      </div>

      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      {message ? <div className="alert alert-success">{message}</div> : null}

      {loading ? <div className="card">Loading settings…</div> : null}

      {!loading && activeTab === "general" ? (
        <div className="card">
          <div className="workspace-section-intro">
            <div>
              <h2>General</h2>
              <p>Core tenant defaults and structured runtime preferences.</p>
            </div>
          </div>
          <div className="form-row">
            <label htmlFor="default-provider" className="field-label-required">Default AI provider</label>
            <select
              id="default-provider"
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
          <p className="workspace-meta">Required foundation: set default routing before connector/provider tests.</p>
          <div className="form-row">
            <label htmlFor="ui-prefs">UI preferences (JSON)</label>
            <textarea
              id="ui-prefs"
              value={uiPrefsText}
              onChange={(e) => setUiPrefsText(e.target.value)}
              disabled={!canEdit || saving}
            />
          </div>
          <div className="form-row">
            <label htmlFor="llm-keys">LLM keys (JSON)</label>
            <textarea
              id="llm-keys"
              value={llmKeysText}
              onChange={(e) => setLlmKeysText(e.target.value)}
              disabled={!canEdit || saving}
            />
          </div>
          <div className="form-row">
            <label htmlFor="rag-config">RAG config (JSON)</label>
            <textarea
              id="rag-config"
              value={ragConfigText}
              onChange={(e) => setRagConfigText(e.target.value)}
              disabled={!canEdit || saving}
            />
          </div>
          <button className="btn btn-primary" type="button" disabled={!canEdit || saving} onClick={handleSaveGeneral}>
            {saving ? "Saving…" : "Save general settings"}
          </button>
        </div>
      ) : null}

      {!loading && activeTab === "connectors" ? (
        <div className="card">
          <div className="workspace-section-intro">
            <div>
              <h2>Integrate connectors</h2>
              <p>Enable connectors, provide required config + credentials, validate, then save.</p>
            </div>
            <div className="workspace-meta">Required fields vary by connector type</div>
          </div>
          {Object.keys(connectorDraft)
            .sort()
            .map((name) => {
              const draft = connectorDraft[name];
              const status = connectorStatus(name);
              return (
                <div key={name} className="config-block">
                  <h3>{name}</h3>
                  <div className="field-hint" style={{ marginBottom: "0.55rem" }}>
                    {CONNECTOR_HELP[name] ?? "Set connector config and validate."}
                  </div>
                  <div className="form-row">
                    <label>
                      <input
                        type="checkbox"
                        checked={draft.enabled}
                        onChange={(e) =>
                          setConnectorDraft((prev) => ({ ...prev, [name]: { ...prev[name], enabled: e.target.checked } }))
                        }
                        disabled={!canEdit || saving}
                      />{" "}
                      Enabled
                    </label>
                  </div>
                  <div className="form-row">
                    <label>Config JSON</label>
                    <textarea
                      value={JSON.stringify(draft.config_json ?? {}, null, 2)}
                      onChange={(e) => {
                        try {
                          const parsed = JSON.parse(e.target.value || "{}") as Record<string, unknown>;
                          setConnectorDraft((prev) => ({ ...prev, [name]: { ...prev[name], config_json: parsed } }));
                        } catch {
                          // keep textarea editable; invalid JSON will be rejected on save
                        }
                      }}
                      disabled={!canEdit || saving}
                    />
                  </div>
                  <div className="form-row">
                    <label>Credentials JSON</label>
                    <textarea
                      value={JSON.stringify(draft.credentials_json ?? {}, null, 2)}
                      onChange={(e) => {
                        try {
                          const parsed = JSON.parse(e.target.value || "{}") as Record<string, unknown>;
                          setConnectorDraft((prev) => ({ ...prev, [name]: { ...prev[name], credentials_json: parsed } }));
                        } catch {
                          // keep editable
                        }
                      }}
                      disabled={!canEdit || saving}
                    />
                  </div>
                  <div className="actions">
                    <span className={`status-chip ${status?.enabled ? "succeeded" : "queued"}`}>
                      {status?.enabled ? "connected" : "not connected"}
                    </span>
                    <button
                      className="btn btn-ghost"
                      type="button"
                      onClick={() => handleValidateConnector(name)}
                      disabled={!canEdit || saving}
                    >
                      Validate
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
          <button className="btn btn-primary" type="button" disabled={!canEdit || saving} onClick={handleSaveConnectors}>
            {saving ? "Saving…" : "Save connector settings"}
          </button>
        </div>
      ) : null}

      {!loading && activeTab === "ai" ? (
        <div className="card">
          <div className="workspace-section-intro">
            <div>
              <h2>AI providers</h2>
              <p>Configure routing, validate connectivity, then verify runtime usage.</p>
            </div>
            <div className="workspace-meta">Save config before running smoke tests</div>
          </div>
          <div className="form-row">
            <label htmlFor="default-provider-ai" className="field-label-required">Default provider</label>
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
                <h3>{name}</h3>
                <div className="form-row">
                  <label>
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
                    <label>Temperature (advanced)</label>
                    <input
                      value={draft.temperature}
                      onChange={(e) =>
                        setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], temperature: e.target.value } }))
                      }
                      disabled={!canEdit || saving}
                    />
                  </div>
                  <div className="form-row">
                    <label>Max tokens (advanced)</label>
                    <input
                      value={draft.max_tokens}
                      onChange={(e) =>
                        setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], max_tokens: e.target.value } }))
                      }
                      disabled={!canEdit || saving}
                    />
                  </div>
                  <div className="form-row">
                    <label>Endpoint URL (required for Azure/OpenAI compatible)</label>
                    <input
                      value={draft.endpoint_url}
                      onChange={(e) =>
                        setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], endpoint_url: e.target.value } }))
                      }
                      disabled={!canEdit || saving}
                    />
                  </div>
                  <div className="form-row">
                    <label>API key ref</label>
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
                    <label className="field-label-required">API key (encrypted)</label>
                    <input
                      type="password"
                      value={draft.api_key}
                      onChange={(e) =>
                        setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], api_key: e.target.value } }))
                      }
                      disabled={!canEdit || saving}
                    />
                  </div>
                  <div className="form-row">
                    <label>Timeout seconds (advanced)</label>
                    <input
                      value={draft.timeout_seconds}
                      onChange={(e) =>
                        setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], timeout_seconds: e.target.value } }))
                      }
                      disabled={!canEdit || saving}
                    />
                  </div>
                  <div className="form-row">
                    <label>Retry count (advanced)</label>
                    <input
                      value={draft.retry_count}
                      onChange={(e) =>
                        setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], retry_count: e.target.value } }))
                      }
                      disabled={!canEdit || saving}
                    />
                  </div>
                </div>
                <div className="actions">
                  <span className={`status-chip ${status?.enabled ? "succeeded" : "queued"}`}>
                    {status?.enabled ? "configured" : "not configured"}
                  </span>
                  <button
                    className="btn btn-ghost"
                    type="button"
                    onClick={() => handleValidateProvider(name)}
                    disabled={!canEdit || saving}
                  >
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
            <h3>Use AI Runtime Check</h3>
            <div className="form-row">
              <label>Smoke test prompt</label>
              <textarea value={aiTestPrompt} onChange={(e) => setAiTestPrompt(e.target.value)} disabled={!canEdit || saving} />
            </div>
            <div className="actions">
              <button className="btn btn-ghost" type="button" onClick={handleAiRuntimeSmokeTest} disabled={!canEdit || saving}>
                Run AI runtime smoke test
              </button>
            </div>
          </div>
          <button className="btn btn-primary" type="button" disabled={!canEdit || saving} onClick={handleSaveProviders}>
            {saving ? "Saving…" : "Save AI provider settings"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
