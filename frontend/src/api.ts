const API = "/api/v1";

export type UserPublic = {
  id: number;
  email: string;
  is_superadmin: boolean;
  is_admin: boolean;
  tenant_id: number | null;
  tenant_slug: string | null;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserPublic;
};

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ");
    }
    return res.statusText;
  } catch {
    return res.statusText;
  }
}

export type SignupStatus = {
  tenant_signup_enabled: boolean;
};

export async function fetchSignupStatus(): Promise<SignupStatus> {
  const r = await fetch(`${API}/auth/signup-status`);
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<SignupStatus>;
}

export type TenantSignupBody = {
  organization_name: string;
  tenant_slug: string;
  admin_email: string;
  password: string;
};

export async function signupTenant(body: TenantSignupBody): Promise<LoginResponse> {
  const r = await fetch(`${API}/auth/signup-tenant`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<LoginResponse>;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const r = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<LoginResponse>;
}

export async function fetchMe(token: string): Promise<UserPublic> {
  const r = await fetch(`${API}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<UserPublic>;
}

export type TenantRow = {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  user_count: number;
};

export async function fetchTenants(token: string): Promise<TenantRow[]> {
  const r = await fetch(`${API}/admin/tenants`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<TenantRow[]>;
}

export async function createTenant(
  token: string,
  body: { name: string; slug: string }
): Promise<TenantRow> {
  const r = await fetch(`${API}/admin/tenants`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<TenantRow>;
}

export type PromptLibrary = {
  prompts: { id: string; text: string; tags?: string[] }[];
};

export async function fetchPromptLibrary(): Promise<PromptLibrary> {
  const r = await fetch(`${API}/prompts/library`);
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<PromptLibrary>;
}

export type GovernanceRunResult = Record<string, unknown>;

export async function runGovernance(
  token: string,
  prompt: string,
  promptId?: string | null,
  tenantSlug?: string | null
): Promise<GovernanceRunResult> {
  const q = tenantSlug ? `?tenant_slug=${encodeURIComponent(tenantSlug)}` : "";
  const r = await fetch(`${API}/governance/run${q}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ prompt, prompt_id: promptId ?? null }),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceRunResult>;
}

export async function runGovernanceBatch(token: string): Promise<unknown> {
  const r = await fetch(`${API}/governance/batch`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json();
}

export type TenantSettings = {
  tenant_slug: string;
  default_ai_provider: string | null;
  ui_preferences: Record<string, unknown>;
};

export type TenantSettingsPatch = {
  default_ai_provider?: string | null;
  ui_preferences?: Record<string, unknown>;
};

export type ConnectorConfig = {
  connector_name: string;
  enabled: boolean;
  config_json: Record<string, unknown>;
  last_validation_ok: boolean | null;
  last_validation_error: string | null;
  last_validated_at: string | null;
};

export type ProviderConfig = {
  provider_name: string;
  enabled: boolean;
  model_name: string | null;
  temperature: number | null;
  max_tokens: number | null;
  endpoint_url: string | null;
  api_key_ref: string | null;
  timeout_seconds: number | null;
  retry_count: number | null;
  metadata_json: Record<string, unknown>;
  last_validation_ok: boolean | null;
  last_validation_error: string | null;
  last_validated_at: string | null;
};

export type ProviderSetOut = {
  default_provider: string | null;
  providers: ProviderConfig[];
};

function tenantQuery(tenantSlug?: string | null): string {
  if (!tenantSlug) return "";
  return `?tenant_slug=${encodeURIComponent(tenantSlug)}`;
}

export async function fetchTenantSettings(token: string, tenantSlug?: string | null): Promise<TenantSettings> {
  const r = await fetch(`${API}/tenant/settings${tenantQuery(tenantSlug)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<TenantSettings>;
}

export async function patchTenantSettings(
  token: string,
  body: TenantSettingsPatch,
  tenantSlug?: string | null
): Promise<TenantSettings> {
  const r = await fetch(`${API}/tenant/settings${tenantQuery(tenantSlug)}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<TenantSettings>;
}

export async function fetchConnectorConfigs(token: string, tenantSlug?: string | null): Promise<ConnectorConfig[]> {
  const r = await fetch(`${API}/tenant/connectors${tenantQuery(tenantSlug)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ConnectorConfig[]>;
}

export async function saveConnectorConfigs(
  token: string,
  connectors: Record<string, { enabled: boolean; config_json: Record<string, unknown> }>,
  tenantSlug?: string | null
): Promise<ConnectorConfig[]> {
  const r = await fetch(`${API}/tenant/connectors${tenantQuery(tenantSlug)}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ connectors }),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ConnectorConfig[]>;
}

export async function validateConnectorConfig(
  token: string,
  connectorName: string,
  tenantSlug?: string | null
): Promise<ConnectorConfig> {
  const r = await fetch(`${API}/tenant/connectors/${encodeURIComponent(connectorName)}/validate${tenantQuery(tenantSlug)}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ConnectorConfig>;
}

export async function fetchProviderConfigs(token: string, tenantSlug?: string | null): Promise<ProviderSetOut> {
  const r = await fetch(`${API}/tenant/ai/providers${tenantQuery(tenantSlug)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ProviderSetOut>;
}

export async function saveProviderConfigs(
  token: string,
  body: {
    default_provider?: string | null;
    providers: Record<
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
    >;
  },
  tenantSlug?: string | null
): Promise<ProviderSetOut> {
  const r = await fetch(`${API}/tenant/ai/providers${tenantQuery(tenantSlug)}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ProviderSetOut>;
}

export async function validateProviderConfig(
  token: string,
  providerName: string,
  tenantSlug?: string | null
): Promise<ProviderConfig> {
  const r = await fetch(
    `${API}/tenant/ai/providers/${encodeURIComponent(providerName)}/validate${tenantQuery(tenantSlug)}`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ProviderConfig>;
}

export type GovernanceRunV1 = {
  id: number;
  status: string;
  prompt: string;
  prompt_id: string | null;
  tenant_id: number | null;
  retry_count: number;
  error_message: string | null;
  runtime_config_json: Record<string, unknown>;
  result_json: Record<string, unknown> | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type GovernanceCase = {
  id: number;
  tenant_id: number | null;
  title: string;
  status: string;
  owner_user_id: number | null;
  latest_run_id: number | null;
  created_by_user_id: number;
  created_at: string;
  updated_at: string;
};

export type Decision = {
  id: number;
  case_id: number;
  run_id: number | null;
  status: string;
  recommended_action: string | null;
  final_action: string | null;
  rationale: string | null;
  approved_by_user_id: number | null;
  approved_at: string | null;
  created_by_user_id: number;
  created_at: string;
};

export type AuditEvent = {
  id: number;
  tenant_id: number | null;
  actor_user_id: number;
  area: string;
  action: string;
  entity_type: string | null;
  entity_id: number | null;
  severity: string;
  summary: string;
  created_at: string;
};

export async function createGovernanceRun(
  token: string,
  body: { prompt: string; prompt_id?: string | null },
  tenantSlug?: string | null
): Promise<GovernanceRunV1> {
  const r = await fetch(`${API}/governance/runs${tenantQuery(tenantSlug)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceRunV1>;
}

export async function fetchGovernanceRun(token: string, runId: number): Promise<GovernanceRunV1> {
  const r = await fetch(`${API}/governance/runs/${runId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceRunV1>;
}

export async function fetchGovernanceRuns(
  token: string,
  params?: { status?: string; limit?: number }
): Promise<GovernanceRunV1[]> {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.limit) search.set("limit", String(params.limit));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  const r = await fetch(`${API}/governance/runs${suffix}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceRunV1[]>;
}

export async function createCase(
  token: string,
  body: { title: string; run_id?: number | null; owner_user_id?: number | null },
  tenantSlug?: string | null
): Promise<GovernanceCase> {
  const r = await fetch(`${API}/governance/cases${tenantQuery(tenantSlug)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceCase>;
}

export async function fetchCases(token: string, limit = 100): Promise<GovernanceCase[]> {
  const r = await fetch(`${API}/governance/cases?limit=${limit}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceCase[]>;
}

export async function updateCase(
  token: string,
  caseId: number,
  body: { status?: string; owner_user_id?: number | null; latest_run_id?: number | null }
): Promise<GovernanceCase> {
  const r = await fetch(`${API}/governance/cases/${caseId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceCase>;
}

export async function createDecision(
  token: string,
  caseId: number,
  body: { run_id?: number | null; recommended_action?: string | null; rationale?: string | null }
): Promise<Decision> {
  const r = await fetch(`${API}/governance/cases/${caseId}/decisions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<Decision>;
}

export async function approveDecision(
  token: string,
  decisionId: number,
  body: { final_action: string; rationale?: string | null }
): Promise<Decision> {
  const r = await fetch(`${API}/governance/decisions/${decisionId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<Decision>;
}

export async function fetchAuditEvents(token: string, area?: string): Promise<AuditEvent[]> {
  const q = area ? `?area=${encodeURIComponent(area)}` : "";
  const r = await fetch(`${API}/governance/audit-events${q}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<AuditEvent[]>;
}

export async function fetchRunSummaryReport(
  token: string,
  format: "json" | "csv",
  limit = 200
): Promise<{ count: number; items: Record<string, unknown>[] } | Blob> {
  const r = await fetch(`${API}/reports/runs/summary?format=${format}&limit=${limit}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  if (format === "csv") return r.blob();
  return r.json();
}

export async function fetchAuditExport(
  token: string,
  format: "json" | "csv",
  area?: string
): Promise<{ count: number; items: Record<string, unknown>[] } | Blob> {
  const q = new URLSearchParams();
  q.set("format", format);
  if (area) q.set("area", area);
  const r = await fetch(`${API}/reports/audit-events?${q.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  if (format === "csv") return r.blob();
  return r.json();
}
