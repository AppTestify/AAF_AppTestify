import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
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
  type ProviderConfig,
  type TenantNotificationConfig,
  type TenantRow,
  type UserPublic,
} from "../api";
import { WorkspacePageShell } from "../components/layout/WorkspacePageShell";
import { SegmentedTabs } from "../components/ui/SegmentedTabs";
import { AIProvidersTab } from "./settings/AIProvidersTab";
import { ConnectorsTab } from "./settings/ConnectorsTab";
import { GeneralTab } from "./settings/GeneralTab";
import { UsersTab } from "./settings/UsersTab";
import {
  PROVIDERS,
  type ConnectorDraft,
  type ProviderDraft,
  type SettingsTab,
} from "./settings/types";

type WorkspaceSettingsPageProps = {
  user: UserPublic;
  tenants: TenantRow[] | null;
  initialTab?: SettingsTab;
};

export function WorkspaceSettingsPage({ user, tenants, initialTab = "general" }: WorkspaceSettingsPageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabFromUrl = (searchParams.get("tab") as SettingsTab | null) ?? initialTab;
  const [activeTab, setActiveTab] = useState<SettingsTab>(tabFromUrl);
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
  const [teamsWebhook, setTeamsWebhook] = useState("");
  const [clearTeamsWebhook, setClearTeamsWebhook] = useState(false);
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
    const next = (searchParams.get("tab") as SettingsTab | null) ?? initialTab;
    setActiveTab(next);
  }, [searchParams, initialTab]);

  const handleTabChange = (id: string) => {
    const tab = id as SettingsTab;
    setActiveTab(tab);
    const next = new URLSearchParams(searchParams);
    next.set("tab", tab);
    setSearchParams(next, { replace: true });
  };

  useEffect(() => {
    if (!user.is_superadmin) return;
    if (!targetTenantSlug && tenantOptions.length > 0) setTargetTenantSlug(tenantOptions[0]);
  }, [user.is_superadmin, tenantOptions, targetTenantSlug]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      fetchTenantSettings(targetForApi),
      fetchConnectorConfigs(targetForApi),
      fetchProviderConfigs(targetForApi),
      fetchNotificationConfig(targetForApi),
      fetchRbacUsers(targetForApi),
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
  }, [targetForApi]);

  const handleSaveGeneral = async () => {
    try {
      setSaving(true);
      setMessage(null);
      const prefs = JSON.parse(uiPrefsText || "{}") as Record<string, unknown>;
      const llmKeys = JSON.parse(llmKeysText || "{}") as Record<string, string>;
      const ragConfig = JSON.parse(ragConfigText || "{}") as Record<string, unknown>;
      await patchTenantSettings(
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
      const payload: Parameters<typeof saveNotificationConfig>[0] = {
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
        notification_channels: notificationCfg.notification_channels,
        digest_schedule: notificationCfg.digest_schedule,
        clear_slack_incoming_webhook: clearSlackWebhook,
        clear_teams_incoming_webhook: clearTeamsWebhook,
        templates: notificationCfg.templates,
      };
      if (slackWebhook.trim()) {
        payload.slack_incoming_webhook = slackWebhook.trim();
      }
      if (teamsWebhook.trim()) {
        payload.teams_incoming_webhook = teamsWebhook.trim();
      }
      const saved = await saveNotificationConfig(payload, targetForApi);
      setNotificationCfg(saved);
      setSmtpPassword("");
      setSlackWebhook("");
      setClearSlackWebhook(false);
      setTeamsWebhook("");
      setClearTeamsWebhook(false);
      setMessage("SMTP, webhooks, channels, and notification templates saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save notification config");
    } finally {
      setSaving(false);
    }
  };

  const handleTestSmtp = async () => {
    try {
      setSaving(true);
      const result = await testNotificationConfig({ to_email: smtpTestEmail || null }, targetForApi);
      setMessage(result.message);
      const refreshed = await fetchNotificationConfig(targetForApi);
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
      const created = await createRbacUser({ email: newUserEmail.trim(), role_name: newUserRole, is_active: true }, targetForApi);
      setNewUserEmail("");
      setMessage(
        created.temporary_password
          ? `User created. Email delivery: ${created.delivery_status}. Temporary password: ${created.temporary_password}`
          : `User created and credentials sent by email.`
      );
      setAdminUsers(await fetchRbacUsers(targetForApi));
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
      const saved = await saveConnectorConfigs(connectorDraft, targetForApi);
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
      const saved = await saveConnectorConfigs(connectorDraft, targetForApi);
      setConnectorRows(saved);
      syncDraftFromSavedConnectors(saved);
      const validated = await validateConnectorConfig(name, targetForApi);
      setConnectorRows((prev) =>
        prev.map((c) => (c.connector_name === name ? validated : c)).concat(prev.some((c) => c.connector_name === name) ? [] : [validated])
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
      const validated = await validateConnectorConfig(name, targetForApi);
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
          model_name: d.model_name?.trim() || null,
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
      const validated = await validateProviderConfig(provider, targetForApi);
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
      const result = await runGovernance(aiTestPrompt, "ai-runtime-smoke", targetForApi);
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

  const connectorStatus = (name: string): ConnectorConfig | undefined => connectorRows.find((c) => c.connector_name === name);
  const providerStatus = (name: string): ProviderConfig | undefined => providerRows.find((p) => p.provider_name === name);

  return (
    <WorkspacePageShell variant="operational" title="Settings" subtitle="Tenant configuration, connectors, and AI providers">
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

      <SegmentedTabs
        tabs={[
          { id: "general", label: "General" },
          { id: "connectors", label: "Connectors" },
          { id: "ai", label: "AI Providers" },
          { id: "users", label: "Users & Notifications" },
        ]}
        activeId={activeTab}
        onChange={handleTabChange}
      />

      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      {message ? <div className="alert alert-success">{message}</div> : null}

      {loading ? <div className="card">Loading settings…</div> : null}

      {!loading && activeTab === "general" ? (
        <GeneralTab
          canEdit={canEdit}
          saving={saving}
          defaultProvider={defaultProvider}
          setDefaultProvider={setDefaultProvider}
          uiPrefsText={uiPrefsText}
          setUiPrefsText={setUiPrefsText}
          llmKeysText={llmKeysText}
          setLlmKeysText={setLlmKeysText}
          ragConfigText={ragConfigText}
          setRagConfigText={setRagConfigText}
          onSave={() => void handleSaveGeneral()}
        />
      ) : null}

      {!loading && activeTab === "connectors" ? (
        <ConnectorsTab
          canEdit={canEdit}
          saving={saving}
          connectorDraft={connectorDraft}
          setConnectorDraft={setConnectorDraft}
          connectorRows={connectorRows}
          mergeConnectorConfig={mergeConnectorConfig}
          mergeConnectorCreds={mergeConnectorCreds}
          connectorStatus={connectorStatus}
          onSaveAll={() => void handleSaveConnectors()}
          onSaveAndTest={handleSaveAndTestConnector}
          onValidate={handleValidateConnector}
        />
      ) : null}

      {!loading && activeTab === "ai" ? (
        <AIProvidersTab
          canEdit={canEdit}
          saving={saving}
          defaultProvider={defaultProvider}
          setDefaultProvider={setDefaultProvider}
          providerDraft={providerDraft}
          setProviderDraft={setProviderDraft}
          providerStatus={providerStatus}
          aiTestPrompt={aiTestPrompt}
          setAiTestPrompt={setAiTestPrompt}
          onSave={() => void handleSaveProviders()}
          onValidate={handleValidateProvider}
          onRuntimeCheck={() => void handleAiRuntimeSmokeTest()}
        />
      ) : null}

      {!loading && activeTab === "users" ? (
        <UsersTab
          canEdit={canEdit}
          saving={saving}
          adminUsers={adminUsers}
          newUserEmail={newUserEmail}
          setNewUserEmail={setNewUserEmail}
          newUserRole={newUserRole}
          setNewUserRole={setNewUserRole}
          onAddUser={() => void handleAddUser()}
          notificationCfg={notificationCfg}
          setNotificationCfg={setNotificationCfg}
          smtpPassword={smtpPassword}
          setSmtpPassword={setSmtpPassword}
          smtpTestEmail={smtpTestEmail}
          setSmtpTestEmail={setSmtpTestEmail}
          slackWebhook={slackWebhook}
          setSlackWebhook={setSlackWebhook}
          clearSlackWebhook={clearSlackWebhook}
          setClearSlackWebhook={setClearSlackWebhook}
          teamsWebhook={teamsWebhook}
          setTeamsWebhook={setTeamsWebhook}
          clearTeamsWebhook={clearTeamsWebhook}
          setClearTeamsWebhook={setClearTeamsWebhook}
          onTestSmtp={() => void handleTestSmtp()}
          onSaveNotifications={() => void handleSaveNotifications()}
        />
      ) : null}
    </WorkspacePageShell>
  );
}
