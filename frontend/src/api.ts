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

export type AccessLead = {
  id: number;
  organization_name: string;
  contact_name: string;
  work_email: string;
  website: string;
  notes: string;
  status: string;
  converted_tenant_id: number | null;
  created_at: string;
  updated_at: string;
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

export async function submitRequestAccessLead(body: {
  organization_name: string;
  contact_name: string;
  work_email: string;
  website?: string;
  notes?: string;
}): Promise<AccessLead> {
  const r = await fetch(`${API}/leads/request-access`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<AccessLead>;
}

export async function fetchLeads(token: string): Promise<AccessLead[]> {
  const r = await fetch(`${API}/leads`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<AccessLead[]>;
}

export async function convertLeadToTenant(
  token: string,
  leadId: number,
  body: { tenant_name: string; tenant_slug: string }
): Promise<AccessLead> {
  const r = await fetch(`${API}/leads/${leadId}/convert`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<AccessLead>;
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
  rag_config_json: Record<string, unknown>;
  llm_keys_configured: string[];
};

export type TenantSettingsPatch = {
  default_ai_provider?: string | null;
  ui_preferences?: Record<string, unknown>;
  rag_config_json?: Record<string, unknown>;
  llm_keys?: Record<string, string>;
};

export type ConnectorConfig = {
  connector_name: string;
  enabled: boolean;
  config_json: Record<string, unknown>;
  credentials_json: Record<string, unknown>;
  last_validation_ok: boolean | null;
  last_validation_error: string | null;
  last_validated_at: string | null;
  telemetry_json: Record<string, unknown>;
  last_sync_at: string | null;
};

export type ProviderConfig = {
  provider_name: string;
  enabled: boolean;
  model_name: string | null;
  temperature: number | null;
  max_tokens: number | null;
  endpoint_url: string | null;
  api_key_ref: string | null;
  api_key: string | null;
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
  connectors: Record<string, { enabled: boolean; config_json: Record<string, unknown>; credentials_json: Record<string, unknown> }>,
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
        api_key?: string | null;
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

export type DashboardSummary = {
  runs_total: number;
  runs_24h: number;
  runs_success_24h: number;
  cases_open: number;
  cases_total: number;
  alerts_24h: number;
  connectors_enabled: number;
  connectors_total: number;
  providers_enabled: number;
  providers_total: number;
  run_status_counts: Record<string, number>;
  case_status_counts: Record<string, number>;
  recent_runs: { id: number; status: string; prompt: string; created_at: string }[];
  recent_alerts: { id: number; area: string; action: string; severity: string; summary: string; created_at: string }[];
  connector_health: {
    connector_name: string;
    enabled: boolean;
    last_validation_ok: boolean | null;
    last_validation_error: string | null;
    last_validated_at: string | null;
  }[];
  provider_health: {
    provider_name: string;
    enabled: boolean;
    last_validation_ok: boolean | null;
    last_validation_error: string | null;
    last_validated_at: string | null;
  }[];
  integration_coverage_pct: number;
  integration_fresh_pct: number;
};

export async function fetchDashboardSummary(token: string): Promise<DashboardSummary> {
  const r = await fetch(`${API}/telemetry/summary`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<DashboardSummary>;
}

export type ObservabilitySummary = {
  window_seconds: number;
  uptime_seconds: number;
  requests_total: number;
  requests_per_min: number;
  error_rate: number;
  latency_ms_p50: number;
  latency_ms_p95: number;
  latency_ms_p99: number;
  inflight_requests: number;
  run_queue_depth: number;
  runs_total: number;
  runs_succeeded: number;
  runs_failed: number;
  runs_retried: number;
  run_latency_ms_p95: number;
  endpoints_top: { endpoint: string; count: number; errors: number }[];
  slo_burn_rate: {
    short_window_seconds: number;
    long_window_seconds: number;
    short_error_rate: number;
    long_error_rate: number;
    target: number;
    error_budget: number;
    short_burn_rate: number;
    long_burn_rate: number;
    state: string;
  };
  alert_rules: {
    id: string;
    name: string;
    triggered: boolean;
    severity: string;
    threshold: number;
    current_value: number;
  }[];
  spans_recent: {
    name: string;
    duration_ms: number;
    status: string;
    attributes: Record<string, unknown>;
    ts: number;
  }[];
  connector_calls_total: number;
  connector_error_rate: number;
  connector_latency_ms_p95: number;
  connector_status_counts: Record<string, number>;
  connector_error_categories: Record<string, number>;
  failure_recovery: {
    dead_letter_count: number;
    run_retry_events: number;
  };
};

export async function fetchObservabilitySummary(token: string, windowSeconds = 300): Promise<ObservabilitySummary> {
  const r = await fetch(`${API}/telemetry/observability/summary?window_seconds=${windowSeconds}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ObservabilitySummary>;
}

export type DecisionLifecycle = {
  connectors: {
    github: Record<string, unknown>;
    jira: Record<string, unknown>;
    azure: Record<string, unknown>;
    coverage_total: number;
    fresh_connectors: number;
  };
  telemetry: {
    requests_per_min: number;
    error_rate: number;
    latency_ms_p95: number;
    slo_state: string;
    connector_error_rate: number;
  };
  governance: {
    runs_total: number;
    runs_succeeded: number;
    cases_total: number;
    cases_open: number;
    decisions_total: number;
    decisions_approved: number;
    evidence_total: number;
    audit_events_total: number;
  };
  release: {
    github_success_rate: number;
    github_failing_checks: number;
    jira_blocked_tickets: number;
    azure_release_readiness: string;
    azure_build_success_rate: number;
    release_confidence: number;
    status: string;
  };
  defendability: {
    outcome_traceability_score: number;
    defendable: boolean;
    explainability_basis: string[];
  };
};

export async function fetchDecisionLifecycle(token: string): Promise<DecisionLifecycle> {
  const r = await fetch(`${API}/telemetry/decision-lifecycle`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<DecisionLifecycle>;
}

export type IntelligenceIncident = {
  id: number;
  run_id: number;
  tenant_id: number | null;
  title: string;
  severity: string;
  status: string;
  confidence: number;
  consensus_score: number;
  conflict_detected: boolean;
  evidence_json: Record<string, unknown>;
  recommendation_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ConsensusSummary = {
  incidents_total: number;
  avg_consensus_score: number;
  avg_confidence: number;
  conflict_rate: number;
  high_risk_open: number;
};

export type ExecutiveSummary = {
  id: number;
  tenant_id: number | null;
  run_id: number | null;
  summary_type: string;
  title: string;
  content: string;
  xi_score: number;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type ReleaseGovernance = {
  decision: string;
  reason: string;
  consensus_score: number;
  confidence: number;
  risk_level: string;
};

export type RARIteration = {
  id: number;
  tenant_id: number | null;
  incident_id: number;
  iteration_index: number;
  trigger_reason: string;
  confidence_before: number;
  confidence_after: number;
  evidence_enrichment_json: Record<string, unknown>;
  created_at: string;
};

export type WorkflowRun = {
  id: number;
  tenant_id: number | null;
  incident_id: number | null;
  workflow_type: string;
  status: string;
  decision: string | null;
  score: number;
  summary: string;
  output_json: Record<string, unknown>;
  created_at: string;
};

export async function fetchIntelligenceIncidents(token: string, limit = 10): Promise<IntelligenceIncident[]> {
  const r = await fetch(`${API}/intelligence/incidents?limit=${limit}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<IntelligenceIncident[]>;
}

export async function fetchConsensusSummary(token: string): Promise<ConsensusSummary> {
  const r = await fetch(`${API}/intelligence/consensus/summary`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ConsensusSummary>;
}

export async function fetchExecutiveSummaries(token: string, limit = 5): Promise<ExecutiveSummary[]> {
  const r = await fetch(`${API}/intelligence/executive-summaries?limit=${limit}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ExecutiveSummary[]>;
}

export async function fetchReleaseGovernance(token: string): Promise<ReleaseGovernance> {
  const r = await fetch(`${API}/intelligence/release-governance`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ReleaseGovernance>;
}

export async function runRarIteration(token: string, incidentId: number): Promise<RARIteration> {
  const r = await fetch(`${API}/intelligence/incidents/${incidentId}/rar`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<RARIteration>;
}

export async function runGovernanceWorkflow(
  token: string,
  workflowType: string,
  incidentId?: number
): Promise<WorkflowRun> {
  const q = typeof incidentId === "number" ? `?incident_id=${incidentId}` : "";
  const r = await fetch(`${API}/intelligence/workflows/${encodeURIComponent(workflowType)}${q}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<WorkflowRun>;
}

export async function fetchWorkflowRuns(token: string, workflowType?: string): Promise<WorkflowRun[]> {
  const q = workflowType ? `?workflow_type=${encodeURIComponent(workflowType)}` : "";
  const r = await fetch(`${API}/intelligence/workflows${q}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<WorkflowRun[]>;
}

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
  params?: { status?: string; limit?: number; offset?: number; query?: string }
): Promise<GovernanceRunV1[]> {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.limit) search.set("limit", String(params.limit));
  if (typeof params?.offset === "number") search.set("offset", String(params.offset));
  if (params?.query) search.set("prompt_contains", params.query);
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

export async function fetchCasesAdvanced(
  token: string,
  params?: { status?: string; limit?: number; offset?: number; query?: string }
): Promise<GovernanceCase[]> {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (typeof params?.limit === "number") q.set("limit", String(params.limit));
  if (typeof params?.offset === "number") q.set("offset", String(params.offset));
  if (params?.query) q.set("title_contains", params.query);
  const suffix = q.toString() ? `?${q.toString()}` : "";
  const r = await fetch(`${API}/governance/cases${suffix}`, {
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

export async function fetchAuditEvents(
  token: string,
  params?: { area?: string; severity?: string; limit?: number }
): Promise<AuditEvent[]> {
  const q = new URLSearchParams();
  if (params?.area) q.set("area", params.area);
  if (params?.severity) q.set("severity", params.severity);
  if (typeof params?.limit === "number") q.set("limit", String(params.limit));
  const suffix = q.toString() ? `?${q.toString()}` : "";
  const r = await fetch(`${API}/governance/audit-events${suffix}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<AuditEvent[]>;
}

export type EvidenceRow = {
  id: number;
  run_id: number;
  connector_name: string;
  payload_json: Record<string, unknown>;
  created_at: string;
};

export async function fetchEvidence(
  token: string,
  params?: { connector?: string; run_id?: number; limit?: number; offset?: number }
): Promise<EvidenceRow[]> {
  const q = new URLSearchParams();
  if (params?.connector) q.set("connector", params.connector);
  if (typeof params?.run_id === "number") q.set("run_id", String(params.run_id));
  if (typeof params?.limit === "number") q.set("limit", String(params.limit));
  if (typeof params?.offset === "number") q.set("offset", String(params.offset));
  const suffix = q.toString() ? `?${q.toString()}` : "";
  const r = await fetch(`${API}/governance/evidence${suffix}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<EvidenceRow[]>;
}

export async function acknowledgeAlert(token: string, eventId: number): Promise<AuditEvent> {
  const r = await fetch(`${API}/governance/audit-events/${eventId}/acknowledge`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<AuditEvent>;
}

export async function fetchRunSummaryReport(
  token: string,
  format: "json" | "csv",
  limit = 200,
  status?: string
): Promise<{ count: number; items: Record<string, unknown>[] } | Blob> {
  const q = new URLSearchParams();
  q.set("format", format);
  q.set("limit", String(limit));
  if (status) q.set("status", status);
  const r = await fetch(`${API}/reports/runs/summary?${q.toString()}`, {
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
