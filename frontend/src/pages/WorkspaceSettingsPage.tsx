import { useEffect, useMemo, useState } from "react";
import {
  fetchConnectorConfigs,
  fetchProviderConfigs,
  fetchTenantSettings,
  patchTenantSettings,
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
};

type ProviderDraft = {
  enabled: boolean;
  model_name: string;
  temperature: string;
  max_tokens: string;
  endpoint_url: string;
  api_key_ref: string;
  timeout_seconds: string;
  retry_count: string;
  metadata_json: Record<string, unknown>;
};

const PROVIDERS = ["openai", "anthropic", "azure_openai"];

export function WorkspaceSettingsPage({ token, user, tenants, initialTab = "general" }: WorkspaceSettingsPageProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);
  const [targetTenantSlug, setTargetTenantSlug] = useState<string | null>(user.tenant_slug ?? null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [defaultProvider, setDefaultProvider] = useState<string>("");
  const [uiPrefsText, setUiPrefsText] = useState<string>("{}");
  const [connectorRows, setConnectorRows] = useState<ConnectorConfig[]>([]);
  const [connectorDraft, setConnectorDraft] = useState<Record<string, ConnectorDraft>>({});
  const [providerRows, setProviderRows] = useState<ProviderConfig[]>([]);
  const [providerDraft, setProviderDraft] = useState<Record<string, ProviderDraft>>({});

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
        setConnectorRows(connectors);
        const cDraft: Record<string, ConnectorDraft> = {};
        connectors.forEach((c) => {
          cDraft[c.connector_name] = { enabled: c.enabled, config_json: c.config_json ?? {} };
        });
        setConnectorDraft(cDraft);
        setProviderRows(providers.providers);
        const pDraft: Record<string, ProviderDraft> = {};
        providers.providers.forEach((p) => {
          pDraft[p.provider_name] = {
            enabled: p.enabled,
            model_name: p.model_name ?? "",
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
      await patchTenantSettings(
        token,
        {
          default_ai_provider: defaultProvider || null,
          ui_preferences: prefs,
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
      setMessage(`${provider} validated.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Provider validation failed");
    }
  };

  const connectorStatus = (name: string): ConnectorConfig | undefined =>
    connectorRows.find((c) => c.connector_name === name);
  const providerStatus = (name: string): ProviderConfig | undefined => providerRows.find((p) => p.provider_name === name);

  return (
    <div className="app">
      <header className="app-header">
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
      {message ? <div className="alert">{message}</div> : null}

      {loading ? <div className="card">Loading settings…</div> : null}

      {!loading && activeTab === "general" ? (
        <div className="card">
          <h2>General</h2>
          <div className="form-row">
            <label htmlFor="default-provider">Default AI provider</label>
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
          <div className="form-row">
            <label htmlFor="ui-prefs">UI preferences (JSON)</label>
            <textarea
              id="ui-prefs"
              value={uiPrefsText}
              onChange={(e) => setUiPrefsText(e.target.value)}
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
          <h2>Connectors</h2>
          {Object.keys(connectorDraft)
            .sort()
            .map((name) => {
              const draft = connectorDraft[name];
              const status = connectorStatus(name);
              return (
                <div key={name} className="config-block">
                  <h3>{name}</h3>
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
                  <div className="actions">
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
          <h2>AI Providers</h2>
          <div className="form-row">
            <label htmlFor="default-provider-ai">Default provider</label>
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
                <div className="settings-grid">
                  <div className="form-row">
                    <label>Model</label>
                    <input
                      value={draft.model_name}
                      onChange={(e) =>
                        setProviderDraft((prev) => ({ ...prev, [name]: { ...prev[name], model_name: e.target.value } }))
                      }
                      disabled={!canEdit || saving}
                    />
                  </div>
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
                <div className="actions">
                  <button
                    className="btn btn-ghost"
                    type="button"
                    onClick={() => handleValidateProvider(name)}
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
          <button className="btn btn-primary" type="button" disabled={!canEdit || saving} onClick={handleSaveProviders}>
            {saving ? "Saving…" : "Save AI provider settings"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
