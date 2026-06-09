import { useEffect, useMemo, useState } from "react";
import {
  createRbacUser,
  fetchNotificationConfig,
  fetchConnectorConfigs,
  fetchProviderConfigs,
  fetchRbacUsers,
  fetchTenantSettings,
  patchTenantSettings,
  runGovernance,
  saveConnectorConfigs,
  saveNotificationConfig,
  saveProviderConfigs,
  testNotificationConfig,
  validateConnectorConfig,
  validateProviderConfig,
  type AdminUser,
  type ConnectorConfig,
  type NotificationTemplate,
  type ProviderConfig,
  type TenantNotificationConfig,
  type TenantRow,
  type UserPublic,
} from "../api";

type SettingsTab = "general" | "connectors" | "ai" | "users";

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
/** Match live telemetry expectations and server validation. */
const CONNECTOR_ORDER = ["github", "jira", "azure", "aws", "vps", "finops"] as const;

const CONNECTOR_HELP: Record<string, string> = {
  github: "Live: repo slug + PAT. Save, then run connection test.",
  jira: "Live: Jira Cloud/DC base URL, project key, email + API token.",
  azure: "Live: Azure DevOps org + project name, PAT with build/release read.",
  aws: "Account scope only — live AWS telemetry is not available in this build.",
  vps: "Generic custom VPS (Hostinger/others): provider + host required; optional status URL for live health checks.",
  finops: "Path to a local cost export file (JSON/CSV) when FinOps mode is used.",
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
  const [notificationCfg, setNotificationCfg] = useState<TenantNotificationConfig | null>(null);
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpTestEmail, setSmtpTestEmail] = useState("");
  const [slackWebhook, setSlackWebhook] = useState("");
  const [clearSlackWebhook, setClearSlackWebhook] = useState(false);
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([]);
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserRole, setNewUserRole] = useState("reviewer");

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
      fetchNotificationConfig(token, targetForApi),
      fetchRbacUsers(token, targetForApi),
    ])
      .then(([settings, connectors, providers, notifications, users]) => {
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
        setNotificationCfg(notifications);
        setSlackWebhook("");
        setClearSlackWebhook(false);
        setAdminUsers(users);
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

  const handleSaveNotifications = async () => {
    if (!notificationCfg) return;
    try {
      setSaving(true);
      const payload: Parameters<typeof saveNotificationConfig>[1] = {
        smtp_host: notificationCfg.smtp_host,
        smtp_port: notificationCfg.smtp_port,
        smtp_username: notificationCfg.smtp_username,
        smtp_password: smtpPassword || null,
        smtp_from_email: notificationCfg.smtp_from_email,
        use_tls: notificationCfg.use_tls,
        use_ssl: notificationCfg.use_ssl,
        notifications_enabled: notificationCfg.notifications_enabled,
        governance_notify_on_run_complete: notificationCfg.governance_notify_on_run_complete,
        governance_run_notify_emails: notificationCfg.governance_run_notify_emails,
        clear_slack_incoming_webhook: clearSlackWebhook,
        templates: notificationCfg.templates,
      };
      if (slackWebhook.trim()) {
        payload.slack_incoming_webhook = slackWebhook.trim();
      }
      const saved = await saveNotificationConfig(token, payload, targetForApi);
      setNotificationCfg(saved);
      setSmtpPassword("");
      setSlackWebhook("");
      setClearSlackWebhook(false);
      setMessage("SMTP, Slack/email hooks, and notification templates saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save notification config");
    } finally {
      setSaving(false);
    }
  };

  const handleTestSmtp = async () => {
    try {
      setSaving(true);
      const result = await testNotificationConfig(token, { to_email: smtpTestEmail || null }, targetForApi);
      setMessage(result.message);
      const refreshed = await fetchNotificationConfig(token, targetForApi);
      setNotificationCfg(refreshed);
    } catch (e) {
      setError(e instanceof Error ? e.message : "SMTP test failed");
    } finally {
      setSaving(false);
    }
  };

  const handleAddUser = async () => {
    if (!newUserEmail.trim()) return;
    try {
      setSaving(true);
      const created = await createRbacUser(
        token,
        { email: newUserEmail.trim(), role_name: newUserRole, is_active: true },
        targetForApi
      );
      setNewUserEmail("");
      setMessage(
        created.temporary_password
          ? `User created. Email delivery: ${created.delivery_status}. Temporary password: ${created.temporary_password}`
          : `User created and credentials sent by email.`
      );
      setAdminUsers(await fetchRbacUsers(token, targetForApi));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add user");
    } finally {
      setSaving(false);
    }
  };

  const mergeConnectorConfig = (name: string, patch: Record<string, unknown>) => {
    setConnectorDraft((prev) => ({
      ...prev,
      [name]: {
        ...prev[name],
        config_json: { ...(prev[name]?.config_json ?? {}), ...patch },
      },
    }));
  };

  const mergeConnectorCreds = (name: string, patch: Record<string, unknown>) => {
    setConnectorDraft((prev) => ({
      ...prev,
      [name]: {
        ...prev[name],
        credentials_json: { ...(prev[name]?.credentials_json ?? {}), ...patch },
      },
    }));
  };

  const syncDraftFromSavedConnectors = (saved: ConnectorConfig[]) => {
    setConnectorDraft((prev) => {
      const next = { ...prev };
      for (const c of saved) {
        next[c.connector_name] = {
          enabled: c.enabled,
          config_json: { ...(c.config_json ?? {}) },
          credentials_json: { ...(prev[c.connector_name]?.credentials_json ?? {}) },
        };
      }
      return next;
    });
  };

  const handleSaveConnectors = async () => {
    try {
      setSaving(true);
      setMessage(null);
      setError(null);
      const saved = await saveConnectorConfigs(token, connectorDraft, targetForApi);
      setConnectorRows(saved);
      syncDraftFromSavedConnectors(saved);
      setMessage("All connector settings saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save connectors");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAndTestConnector = async (name: string) => {
    try {
      setSaving(true);
      setMessage(null);
      setError(null);
      const saved = await saveConnectorConfigs(token, connectorDraft, targetForApi);
      setConnectorRows(saved);
      syncDraftFromSavedConnectors(saved);
      const validated = await validateConnectorConfig(token, name, targetForApi);
      setConnectorRows((prev) =>
        prev.map((c) => (c.connector_name === name ? validated : c)).concat(
          prev.some((c) => c.connector_name === name) ? [] : [validated]
        )
      );
      if (validated.last_validation_ok) {
        setMessage(`${name}: saved and connection check passed.`);
      } else {
        setMessage(`${name}: saved. Check failed: ${validated.last_validation_error || "see details below"}.`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save or connection test failed");
    } finally {
      setSaving(false);
    }
  };

  const handleValidateConnector = async (name: string) => {
    try {
      setSaving(true);
      setMessage(null);
      setError(null);
      const validated = await validateConnectorConfig(token, name, targetForApi);
      setConnectorRows((prev) =>
        prev.map((c) => (c.connector_name === name ? validated : c)).concat(prev.some((c) => c.connector_name === name) ? [] : [validated])
      );
      setMessage(
        validated.last_validation_ok ? `${name}: connection check passed.` : `${name}: ${validated.last_validation_error || "check failed"}.`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connector validation failed");
    } finally {
      setSaving(false);
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
      const llmInvocation = (result as Record<string, unknown>).llm_invocation as Record<string, unknown> | undefined;
      const llmStatus = String(llmInvocation?.status ?? "unknown");
      setMessage(
        activeProvider
          ? `AI runtime check completed. Active default provider: ${activeProvider}. Invocation status: ${llmStatus}.`
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
        <button className={activeTab === "users" ? "active" : ""} onClick={() => setActiveTab("users")} type="button">
          Users & Notifications
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
                <strong>Connectors tab</strong> — link GitHub, Jira, Azure DevOps; use <em>Save &amp; test</em> on each.
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
              <button className="btn btn-primary" type="button" disabled={!canEdit || saving} onClick={handleSaveGeneral}>
                {saving ? "Saving…" : "Save general settings"}
              </button>
            </div>
          </div>

          <div className="card">
            <details className="settings-advanced-details">
              <summary>Advanced — JSON (UI preferences, LLM key map, RAG)</summary>
              <p className="workspace-meta" style={{ marginTop: "0.5rem" }}>
                For power users. Invalid JSON will fail on save. LLM keys: use real secret values only when updating; placeholder entries are ignored by the
                backend if unchanged.
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
              <button className="btn btn-ghost" type="button" disabled={!canEdit || saving} onClick={handleSaveGeneral}>
                Save advanced JSON
              </button>
            </details>
          </div>
        </div>
      ) : null}

      {!loading && activeTab === "connectors" ? (
        <div className="card settings-connectors-card">
          <div className="workspace-section-intro">
            <div>
              <h2>Connectors</h2>
              <p>
                Use the quick fields for each system, then <strong>Save &amp; test</strong> to store settings and run the connection check in one step. Use{" "}
                <strong>Test only</strong> if you already saved and only want to re-check.
              </p>
            </div>
          </div>
          <p className="field-hint settings-cred-hint">
            Credentials are encrypted when saved and are never returned by the API — re-enter a token or password to update it.
          </p>

          {CONNECTOR_ORDER.map((name) => {
            const draft = connectorDraft[name];
            const status = connectorStatus(name);
            if (!draft) return null;
            const cfg = draft.config_json ?? {};
            const cred = draft.credentials_json ?? {};

            return (
              <div key={name} className="config-block settings-connector-block">
                <div className="settings-connector-head">
                  <h3 className="settings-connector-title">{name}</h3>
                  <label className="settings-enable-inline">
                    <input
                      type="checkbox"
                      checked={draft.enabled}
                      onChange={(e) =>
                        setConnectorDraft((prev) => ({
                          ...prev,
                          [name]: { ...prev[name], enabled: e.target.checked },
                        }))
                      }
                      disabled={!canEdit || saving}
                    />{" "}
                    Enabled
                  </label>
                </div>
                <p className="field-hint">{CONNECTOR_HELP[name] ?? "Configure and test."}</p>

                {name === "github" ? (
                  <div className="config-columns settings-quick-grid">
                    <div className="form-row">
                      <label>Repository</label>
                      <input
                        value={String(cfg.repo ?? "")}
                        onChange={(e) => mergeConnectorConfig(name, { repo: e.target.value })}
                        placeholder="owner/repo"
                        disabled={!canEdit || saving}
                      />
                    </div>
                    <div className="form-row">
                      <label>GitHub token (PAT)</label>
                      <input
                        type="password"
                        autoComplete="off"
                        value={String(cred.token ?? "")}
                        onChange={(e) => mergeConnectorCreds(name, { token: e.target.value })}
                        placeholder={status?.credentials_keys_configured?.includes("token") ? "Configured (masked)" : "ghp_…"}
                        disabled={!canEdit || saving}
                      />
                    </div>
                  </div>
                ) : null}

                {name === "jira" ? (
                  <div className="config-columns settings-quick-grid">
                    <div className="form-row">
                      <label>Jira base URL</label>
                      <input
                        value={String(cfg.base_url ?? "")}
                        onChange={(e) => mergeConnectorConfig(name, { base_url: e.target.value.replace(/\/$/, "") })}
                        placeholder="https://your-domain.atlassian.net"
                        disabled={!canEdit || saving}
                      />
                    </div>
                    <div className="form-row">
                      <label>Project key</label>
                      <input
                        value={String(cfg.project ?? "")}
                        onChange={(e) => mergeConnectorConfig(name, { project: e.target.value.toUpperCase() })}
                        placeholder="PROJ"
                        disabled={!canEdit || saving}
                      />
                    </div>
                    <div className="form-row">
                      <label>Account email</label>
                      <input
                        type="email"
                        value={String(cred.email ?? "")}
                        onChange={(e) => mergeConnectorCreds(name, { email: e.target.value })}
                        placeholder={status?.credentials_keys_configured?.includes("email") ? "Configured (masked)" : "you@company.com"}
                        disabled={!canEdit || saving}
                      />
                    </div>
                    <div className="form-row">
                      <label>API token</label>
                      <input
                        type="password"
                        autoComplete="off"
                        value={String(cred.token ?? "")}
                        onChange={(e) => mergeConnectorCreds(name, { token: e.target.value })}
                        placeholder={status?.credentials_keys_configured?.includes("token") ? "Configured (masked)" : "Enter token"}
                        disabled={!canEdit || saving}
                      />
                    </div>
                  </div>
                ) : null}

                {name === "azure" ? (
                  <div className="config-columns settings-quick-grid">
                    <div className="form-row">
                      <label>Organization</label>
                      <input
                        value={String(cfg.organization ?? "")}
                        onChange={(e) => mergeConnectorConfig(name, { organization: e.target.value })}
                        placeholder="Azure DevOps org name"
                        disabled={!canEdit || saving}
                      />
                    </div>
                    <div className="form-row">
                      <label>Project</label>
                      <input
                        value={String(cfg.project ?? "")}
                        onChange={(e) => mergeConnectorConfig(name, { project: e.target.value })}
                        placeholder="Project name"
                        disabled={!canEdit || saving}
                      />
                    </div>
                    <div className="form-row">
                      <label>Personal access token (PAT)</label>
                      <input
                        type="password"
                        autoComplete="off"
                        value={String(cred.token ?? "")}
                        onChange={(e) => mergeConnectorCreds(name, { token: e.target.value })}
                        placeholder="Build + Release read scopes"
                        disabled={!canEdit || saving}
                      />
                    </div>
                  </div>
                ) : null}

                {name === "aws" ? (
                  <div className="config-columns settings-quick-grid">
                    <div className="form-row">
                      <label>AWS account ID</label>
                      <input
                        value={String(cfg.account_id ?? "")}
                        onChange={(e) => mergeConnectorConfig(name, { account_id: e.target.value })}
                        placeholder="123456789012"
                        disabled={!canEdit || saving}
                      />
                    </div>
                  </div>
                ) : null}

                {name === "finops" ? (
                  <div className="config-columns settings-quick-grid">
                    <div className="form-row">
                      <label>Cost file path</label>
                      <input
                        value={String(cfg.cost_file ?? "")}
                        onChange={(e) => mergeConnectorConfig(name, { cost_file: e.target.value })}
                        placeholder="/path/to/cost-export.json"
                        disabled={!canEdit || saving}
                      />
                    </div>
                  </div>
                ) : null}

                {name === "vps" ? (
                  <div className="config-columns settings-quick-grid">
                    <div className="form-row">
                      <label>Provider</label>
                      <input
                        value={String(cfg.provider ?? "")}
                        onChange={(e) => mergeConnectorConfig(name, { provider: e.target.value })}
                        placeholder="Hostinger"
                        disabled={!canEdit || saving}
                      />
                    </div>
                    <div className="form-row">
                      <label>Host</label>
                      <input
                        value={String(cfg.host ?? "")}
                        onChange={(e) => mergeConnectorConfig(name, { host: e.target.value })}
                        placeholder="vps.example.com"
                        disabled={!canEdit || saving}
                      />
                    </div>
                    <div className="form-row">
                      <label>Status URL (optional)</label>
                      <input
                        value={String(cfg.status_url ?? "")}
                        onChange={(e) => mergeConnectorConfig(name, { status_url: e.target.value })}
                        placeholder="https://vps.example.com/health"
                        disabled={!canEdit || saving}
                      />
                    </div>
                    <div className="form-row">
                      <label>Bearer token (optional)</label>
                      <input
                        type="password"
                        autoComplete="off"
                        value={String(cred.token ?? "")}
                        onChange={(e) => mergeConnectorCreds(name, { token: e.target.value })}
                        placeholder="Token for status URL"
                        disabled={!canEdit || saving}
                      />
                    </div>
                  </div>
                ) : null}

                <div className="actions settings-connector-actions">
                  <span
                    className={`status-chip ${
                      status?.last_validation_ok === true
                        ? "succeeded"
                        : status?.last_validation_ok === false
                          ? "failed"
                          : "queued"
                    }`}
                  >
                    {status?.last_validation_ok === true
                      ? "Check OK"
                      : status?.last_validation_ok === false
                        ? "Check failed"
                        : "Not checked yet"}
                  </span>
                  <button
                    className="btn btn-primary"
                    type="button"
                    onClick={() => void handleSaveAndTestConnector(name)}
                    disabled={!canEdit || saving}
                  >
                    Save &amp; test
                  </button>
                  <button
                    className="btn btn-ghost"
                    type="button"
                    onClick={() => void handleValidateConnector(name)}
                    disabled={!canEdit || saving}
                  >
                    Test only
                  </button>
                  {status?.last_validation_error ? (
                    <span className="settings-validation-msg" title={status.last_validation_error}>
                      {status.last_validation_error}
                    </span>
                  ) : null}
                </div>

                <details className="settings-advanced-details settings-connector-raw">
                  <summary>Edit raw JSON</summary>
                  <div className="form-row">
                    <label>Config JSON</label>
                    <textarea
                      className="settings-json-area"
                      value={JSON.stringify(draft.config_json ?? {}, null, 2)}
                      onChange={(e) => {
                        try {
                          const parsed = JSON.parse(e.target.value || "{}") as Record<string, unknown>;
                          setConnectorDraft((prev) => ({ ...prev, [name]: { ...prev[name], config_json: parsed } }));
                        } catch {
                          /* keep editable */
                        }
                      }}
                      disabled={!canEdit || saving}
                      rows={6}
                    />
                  </div>
                  <div className="form-row">
                    <label>Credentials JSON</label>
                    <textarea
                      className="settings-json-area"
                      value={JSON.stringify(draft.credentials_json ?? {}, null, 2)}
                      onChange={(e) => {
                        try {
                          const parsed = JSON.parse(e.target.value || "{}") as Record<string, unknown>;
                          setConnectorDraft((prev) => ({ ...prev, [name]: { ...prev[name], credentials_json: parsed } }));
                        } catch {
                          /* keep editable */
                        }
                      }}
                      disabled={!canEdit || saving}
                      rows={5}
                    />
                  </div>
                </details>
              </div>
            );
          })}

          <div className="actions settings-connectors-footer">
            <button className="btn btn-ghost" type="button" disabled={!canEdit || saving} onClick={handleSaveConnectors}>
              {saving ? "Saving…" : "Save all connectors (no test)"}
            </button>
          </div>
        </div>
      ) : null}

      {!loading && activeTab === "ai" ? (
        <div className="card">
          <div className="workspace-section-intro">
            <div>
              <h2>AI providers</h2>
              <p>Pick a default provider, add keys, test connection, and save.</p>
            </div>
            <div className="workspace-meta">Keep advanced settings collapsed unless needed</div>
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
                    <label className="field-label-required">API key</label>
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
            <h3>Runtime check</h3>
            <div className="form-row">
              <label>Test prompt</label>
              <textarea value={aiTestPrompt} onChange={(e) => setAiTestPrompt(e.target.value)} disabled={!canEdit || saving} />
            </div>
            <div className="actions">
              <button className="btn btn-ghost" type="button" onClick={handleAiRuntimeSmokeTest} disabled={!canEdit || saving}>
                Run runtime check
              </button>
            </div>
          </div>
          <button className="btn btn-primary" type="button" disabled={!canEdit || saving} onClick={handleSaveProviders}>
            {saving ? "Saving…" : "Save AI provider settings"}
          </button>
        </div>
      ) : null}
      {!loading && activeTab === "users" ? (
        <div className="card">
          <div className="workspace-section-intro">
            <div>
              <h2>Users, SMTP, and notifications</h2>
              <p>Manage RBAC users, SMTP delivery, connection testing, and template content.</p>
            </div>
          </div>
          <div className="config-block">
            <h3>Tenant users</h3>
            <div className="config-columns">
              <div className="form-row">
                <label>Email</label>
                <input value={newUserEmail} onChange={(e) => setNewUserEmail(e.target.value)} placeholder="user@company.com" />
              </div>
              <div className="form-row">
                <label>Role</label>
                <select value={newUserRole} onChange={(e) => setNewUserRole(e.target.value)}>
                  <option value="reviewer">reviewer</option>
                  <option value="tenant_admin">tenant_admin</option>
                </select>
              </div>
            </div>
            <div className="actions">
              <button className="btn btn-primary" type="button" onClick={handleAddUser} disabled={!canEdit || saving}>
                Add user and send password email
              </button>
            </div>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr><th>Email</th><th>Roles</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {adminUsers.map((u) => (
                    <tr key={u.id}>
                      <td>{u.email}</td>
                      <td>{u.role_names.join(", ") || "-"}</td>
                      <td>{u.is_active ? "active" : "disabled"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="config-block">
            <h3>SMTP setup</h3>
            <div className="config-columns">
              <div className="form-row"><label>SMTP host</label><input value={notificationCfg?.smtp_host ?? ""} onChange={(e) => setNotificationCfg((p) => p ? { ...p, smtp_host: e.target.value } : p)} /></div>
              <div className="form-row"><label>SMTP port</label><input value={notificationCfg?.smtp_port ?? ""} onChange={(e) => setNotificationCfg((p) => p ? { ...p, smtp_port: Number(e.target.value || 0) || null } : p)} /></div>
              <div className="form-row"><label>Username</label><input value={notificationCfg?.smtp_username ?? ""} onChange={(e) => setNotificationCfg((p) => p ? { ...p, smtp_username: e.target.value } : p)} /></div>
              <div className="form-row"><label>Password</label><input type="password" value={smtpPassword} onChange={(e) => setSmtpPassword(e.target.value)} placeholder={notificationCfg?.smtp_password_configured ? "Configured (enter to rotate)" : ""} /></div>
              <div className="form-row"><label>From email</label><input value={notificationCfg?.smtp_from_email ?? ""} onChange={(e) => setNotificationCfg((p) => p ? { ...p, smtp_from_email: e.target.value } : p)} /></div>
              <div className="form-row"><label>Test recipient</label><input value={smtpTestEmail} onChange={(e) => setSmtpTestEmail(e.target.value)} placeholder="optional test email" /></div>
            </div>
            <div className="form-row">
              <label><input type="checkbox" checked={notificationCfg?.use_tls ?? true} onChange={(e) => setNotificationCfg((p) => p ? { ...p, use_tls: e.target.checked } : p)} /> Use TLS</label>
              <label><input type="checkbox" checked={notificationCfg?.use_ssl ?? false} onChange={(e) => setNotificationCfg((p) => p ? { ...p, use_ssl: e.target.checked } : p)} /> Use SSL</label>
              <label><input type="checkbox" checked={notificationCfg?.notifications_enabled ?? false} onChange={(e) => setNotificationCfg((p) => p ? { ...p, notifications_enabled: e.target.checked } : p)} /> Enable notifications</label>
            </div>
            <div className="config-block" style={{ marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--border, #ddd)" }}>
              <h3>Governance run delivery</h3>
              <p className="workspace-meta" style={{ marginTop: 0 }}>
                On successful run completion, post to Slack and/or email recipients a signed public link (HTML snapshot + PDF one-pager). For background jobs, set{" "}
                <code>PUBLIC_SHARE_BASE_URL</code> on the API host.
              </p>
              <div className="form-row">
                <label>
                  <input
                    type="checkbox"
                    checked={notificationCfg?.governance_notify_on_run_complete ?? false}
                    onChange={(e) =>
                      setNotificationCfg((p) => (p ? { ...p, governance_notify_on_run_complete: e.target.checked } : p))
                    }
                  />{" "}
                  Notify when a governance run completes
                </label>
              </div>
              <div className="form-row">
                <label>Slack incoming webhook URL</label>
                <input
                  type="url"
                  value={slackWebhook}
                  onChange={(e) => setSlackWebhook(e.target.value)}
                  placeholder={
                    notificationCfg?.slack_webhook_configured
                      ? "Configured (enter a new URL to rotate)"
                      : "https://hooks.slack.com/services/…"
                  }
                />
                <label style={{ marginTop: "0.35rem", display: "block" }}>
                  <input
                    type="checkbox"
                    checked={clearSlackWebhook}
                    onChange={(e) => setClearSlackWebhook(e.target.checked)}
                  />{" "}
                  Remove stored Slack webhook
                </label>
              </div>
              <div className="form-row">
                <label>Digest emails (comma or newline separated; requires SMTP + notifications enabled)</label>
                <textarea
                  rows={3}
                  value={(notificationCfg?.governance_run_notify_emails ?? []).join("\n")}
                  onChange={(e) =>
                    setNotificationCfg((p) =>
                      p
                        ? {
                            ...p,
                            governance_run_notify_emails: e.target.value
                              .split(/[\n,]+/)
                              .map((s) => s.trim())
                              .filter(Boolean),
                          }
                        : p
                    )
                  }
                  placeholder="ops@example.com"
                />
              </div>
            </div>
            <div className="actions">
              <button className="btn btn-ghost" type="button" onClick={handleTestSmtp} disabled={!canEdit || saving}>Test SMTP connection</button>
              <button className="btn btn-primary" type="button" onClick={handleSaveNotifications} disabled={!canEdit || saving}>Save SMTP + templates</button>
            </div>
          </div>
          <div className="config-block">
            <h3>Email templates</h3>
            {Object.entries(notificationCfg?.templates ?? {}).map(([key, tpl]) => (
              <div key={key} className="form-row">
                <label>{key} subject</label>
                <input
                  value={tpl.subject}
                  onChange={(e) =>
                    setNotificationCfg((p) =>
                      p
                        ? { ...p, templates: { ...p.templates, [key]: { ...(p.templates[key] as NotificationTemplate), subject: e.target.value } } }
                        : p
                    )
                  }
                />
                <label>{key} body</label>
                <textarea
                  value={tpl.body}
                  onChange={(e) =>
                    setNotificationCfg((p) =>
                      p ? { ...p, templates: { ...p.templates, [key]: { ...(p.templates[key] as NotificationTemplate), body: e.target.value } } } : p
                    )
                  }
                />
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
