import type { Dispatch, SetStateAction } from "react";
import type { AdminUser, ConnectorConfig, NotificationTemplate, ProviderConfig, TenantNotificationConfig } from "../../api";

export type SettingsTab = "general" | "connectors" | "ai" | "users";

export type ConnectorDraft = {
  enabled: boolean;
  config_json: Record<string, unknown>;
  credentials_json: Record<string, unknown>;
};

export type ProviderDraft = {
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

export const PROVIDERS = ["openai", "anthropic", "azure_openai", "aws_bedrock"];

export const CONNECTOR_ORDER = ["github", "jira", "azure", "aws", "vps", "finops"] as const;

export const CONNECTOR_HELP: Record<string, string> = {
  github: "Live: repo slug + PAT. Save, then run connection test.",
  jira: "Live: Jira base URL, project key, agile board ID (PM sprint tools), email + API token.",
  azure: "Live: Azure DevOps org + project name, PAT with build/release read.",
  aws: "Live FinOps: region + IAM access key/secret for Cost Explorer, Budgets, Auto Scaling, and CloudWatch tools.",
  vps: "Generic custom VPS (Hostinger/others): provider + host required; optional status URL for live health checks.",
  finops: "Optional file fallback (JSON/CSV cost export). When AWS connector is configured, live boto3 tools take precedence.",
};

export type GeneralTabProps = {
  canEdit: boolean;
  saving: boolean;
  defaultProvider: string;
  setDefaultProvider: (v: string) => void;
  uiPrefsText: string;
  setUiPrefsText: (v: string) => void;
  llmKeysText: string;
  setLlmKeysText: (v: string) => void;
  ragConfigText: string;
  setRagConfigText: (v: string) => void;
  onSave: () => void;
};

export type ConnectorsTabProps = {
  canEdit: boolean;
  saving: boolean;
  connectorDraft: Record<string, ConnectorDraft>;
  setConnectorDraft: Dispatch<SetStateAction<Record<string, ConnectorDraft>>>;
  connectorRows: ConnectorConfig[];
  mergeConnectorConfig: (name: string, patch: Record<string, unknown>) => void;
  mergeConnectorCreds: (name: string, patch: Record<string, unknown>) => void;
  connectorStatus: (name: string) => ConnectorConfig | undefined;
  onSaveAll: () => void;
  onSaveAndTest: (name: string) => void;
  onValidate: (name: string) => void;
};

export type AIProvidersTabProps = {
  canEdit: boolean;
  saving: boolean;
  defaultProvider: string;
  setDefaultProvider: (v: string) => void;
  providerDraft: Record<string, ProviderDraft>;
  setProviderDraft: Dispatch<SetStateAction<Record<string, ProviderDraft>>>;
  providerStatus: (name: string) => ProviderConfig | undefined;
  aiTestPrompt: string;
  setAiTestPrompt: (v: string) => void;
  onSave: () => void;
  onValidate: (name: string) => void;
  onRuntimeCheck: () => void;
};

export type UsersTabProps = {
  canEdit: boolean;
  saving: boolean;
  adminUsers: AdminUser[];
  newUserEmail: string;
  setNewUserEmail: (v: string) => void;
  newUserRole: string;
  setNewUserRole: (v: string) => void;
  onAddUser: () => void;
  notificationCfg: TenantNotificationConfig | null;
  setNotificationCfg: Dispatch<SetStateAction<TenantNotificationConfig | null>>;
  smtpPassword: string;
  setSmtpPassword: (v: string) => void;
  smtpTestEmail: string;
  setSmtpTestEmail: (v: string) => void;
  slackWebhook: string;
  setSlackWebhook: (v: string) => void;
  clearSlackWebhook: boolean;
  setClearSlackWebhook: (v: boolean) => void;
  teamsWebhook: string;
  setTeamsWebhook: (v: string) => void;
  clearTeamsWebhook: boolean;
  setClearTeamsWebhook: (v: boolean) => void;
  onTestSmtp: () => void;
  onSaveNotifications: () => void;
};

export type { NotificationTemplate };
