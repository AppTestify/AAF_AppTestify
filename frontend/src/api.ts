const API = "/api/v1";

let refreshPromise: Promise<boolean> | null = null;

const originalFetch = window.fetch;
window.fetch = async function (input, init) {
  const url = typeof input === "string" ? input : (input as Request).url;
  const response = await originalFetch(input, init);
  
  const isRetry = init && (init as any)._isRetry;
  
  if (
    response.status === 401 &&
    !isRetry &&
    !url.includes("/auth/login") &&
    !url.includes("/auth/refresh") &&
    !url.includes("/auth/signup-tenant") &&
    !url.includes("/auth/signup-status") &&
    !url.includes("/auth/logout")
  ) {
    if (!refreshPromise) {
      refreshPromise = (async () => {
        try {
          const refreshRes = await originalFetch(`${API}/auth/refresh`, {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
          });
          if (refreshRes.ok) {
            return true;
          }
        } catch (err) {
          console.error("Token refresh failed:", err);
        }
        return false;
      })();
    }
    
    const isRefreshed = await refreshPromise;
    refreshPromise = null;
    
    if (isRefreshed) {
      const retryInit = { ...(init || {}), _isRetry: true } as RequestInit;
      return originalFetch(input, retryInit);
    }
  }
  
  return response;
};


export type UserPublic = {
  id: number;
  email: string;
  is_superadmin: boolean;
  is_admin: boolean;
  tenant_id: number | null;
  tenant_slug: string | null;
};

export type LoginResponse = {
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
  const r = await fetch(`${API}/auth/signup-status`, { credentials: "include" });
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
  const r = await fetch(`${API}/auth/signup-tenant`, { credentials: "include",
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)});
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
  const r = await fetch(`${API}/leads/request-access`, { credentials: "include",
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<AccessLead>;
}

export async function fetchLeads(): Promise<AccessLead[]> {
  const r = await fetch(`${API}/leads`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<AccessLead[]>;
}

export async function convertLeadToTenant(
  leadId: number,
  body: { tenant_name: string; tenant_slug: string }
): Promise<AccessLead> {
  const r = await fetch(`${API}/leads/${leadId}/convert`, { credentials: "include",
    method: "POST",
    headers: {
      "Content-Type": "application/json"},
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<AccessLead>;
}

export async function logout(): Promise<void> {
  await fetch(`${API}/auth/logout`, { method: "POST", credentials: "include" });
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const r = await fetch(`${API}/auth/login`, { credentials: "include",
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<LoginResponse>;
}

export async function fetchMe(): Promise<UserPublic> {
  const r = await fetch(`${API}/auth/me`, { credentials: "include"});
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

export async function fetchTenants(): Promise<TenantRow[]> {
  const r = await fetch(`${API}/admin/tenants`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<TenantRow[]>;
}

export async function createTenant(
  body: { name: string; slug: string }
): Promise<TenantRow> {
  const r = await fetch(`${API}/admin/tenants`, { credentials: "include",
    method: "POST",
    headers: {
      "Content-Type": "application/json"},
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<TenantRow>;
}

export type PromptLibrary = {
  prompts: { id: string; text: string; tags?: string[] }[];
};

export async function fetchPromptLibrary(): Promise<PromptLibrary> {
  const r = await fetch(`${API}/prompts/library`, { credentials: "include" });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<PromptLibrary>;
}

export type EvidenceRecord = {
  source: string;
  kind: string;
  summary: string;
  severity: number;
  metadata?: Record<string, unknown>;
};

export type AgentOpinion = {
  agent_id: string;
  claim: string;
  confidence: number;
  evidence_refs: string[];
  evidence: string[];
  risk_theme: string;
  raw_signals: Record<string, unknown>;
};

export type UtilityResult = {
  recommended_action: string;
  utility_score: number;
  scores_by_action: Record<string, number>;
  weights_used: Record<string, number>;
  perf_index?: number;
  cost_index?: number;
  risk_index?: number;
  global_utility?: number;
};

export type ConsensusResult = {
  consensus_score: number;
  theme_counts?: Record<string, number>;
  dominant_theme?: string | null;
  notes?: string;
};

export type RARResult = {
  rar_triggered: boolean;
  rar_loops: number;
  consensus_before: number;
  consensus_after: number;
  reground_notes?: string[];
};

export type ExplainabilityResult = {
  xi_score: number;
  checks?: Record<string, boolean>;
};

export type PMFormattedDecision = {
  title: string;
  summary_markdown: string;
  detail_json?: Record<string, unknown>;
};

export type GovernanceRunResult = {
  prompt: string;
  prompt_id?: string | null;
  connectors_used: string[];
  raw_evidence_by_connector: Record<string, unknown>;
  normalized_evidence: EvidenceRecord[];
  agent_opinions: AgentOpinion[];
  consensus: ConsensusResult;
  rar: RARResult;
  utility: UtilityResult;
  explanation: string;
  explainability: ExplainabilityResult;
  pm_view?: PMFormattedDecision;
  decision_framing?: Record<string, unknown>;
  llm_invocation?: Record<string, unknown>;
};

export { formatAgentLabel, parseIncidentFindings } from "./agentLabels";
export type { AgentFinding } from "./agentLabels";

export async function runGovernance(
  prompt: string,
  promptId?: string | null,
  tenantSlug?: string | null
): Promise<GovernanceRunResult> {
  const q = tenantSlug ? `?tenant_slug=${encodeURIComponent(tenantSlug)}` : "";
  const r = await fetch(`${API}/governance/run${q}`, { credentials: "include",
    method: "POST",
    headers: {
      "Content-Type": "application/json"},
    body: JSON.stringify({ prompt, prompt_id: promptId ?? null })});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceRunResult>;
}

export async function runGovernanceBatch(tenantSlug?: string | null): Promise<unknown> {
  const q = tenantSlug ? `?tenant_slug=${encodeURIComponent(tenantSlug)}` : "";
  const r = await fetch(`${API}/governance/batch${q}`, { credentials: "include",
    method: "POST"});
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
  credentials_keys_configured: string[];
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

export async function fetchTenantSettings(tenantSlug?: string | null): Promise<TenantSettings> {
  const r = await fetch(`${API}/tenant/settings${tenantQuery(tenantSlug)}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<TenantSettings>;
}

export async function patchTenantSettings(
  body: TenantSettingsPatch,
  tenantSlug?: string | null
): Promise<TenantSettings> {
  const r = await fetch(`${API}/tenant/settings${tenantQuery(tenantSlug)}`, { credentials: "include",
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"},
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<TenantSettings>;
}

export async function fetchConnectorConfigs(tenantSlug?: string | null): Promise<ConnectorConfig[]> {
  const r = await fetch(`${API}/tenant/connectors${tenantQuery(tenantSlug)}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ConnectorConfig[]>;
}

export async function saveConnectorConfigs(
  connectors: Record<string, { enabled: boolean; config_json: Record<string, unknown>; credentials_json: Record<string, unknown> }>,
  tenantSlug?: string | null
): Promise<ConnectorConfig[]> {
  const r = await fetch(`${API}/tenant/connectors${tenantQuery(tenantSlug)}`, { credentials: "include",
    method: "PUT",
    headers: {
      "Content-Type": "application/json"},
    body: JSON.stringify({ connectors })});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ConnectorConfig[]>;
}

export async function validateConnectorConfig(
  connectorName: string,
  tenantSlug?: string | null
): Promise<ConnectorConfig> {
  const r = await fetch(`${API}/tenant/connectors/${encodeURIComponent(connectorName)}/validate${tenantQuery(tenantSlug)}`, { credentials: "include",
    method: "POST"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ConnectorConfig>;
}

export async function fetchProviderConfigs(tenantSlug?: string | null): Promise<ProviderSetOut> {
  const r = await fetch(`${API}/tenant/ai/providers${tenantQuery(tenantSlug)}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ProviderSetOut>;
}

export async function saveProviderConfigs(
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
  const r = await fetch(`${API}/tenant/ai/providers${tenantQuery(tenantSlug)}`, { credentials: "include",
    method: "PUT",
    headers: {
      "Content-Type": "application/json"},
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ProviderSetOut>;
}

export async function validateProviderConfig(
  providerName: string,
  tenantSlug?: string | null
): Promise<ProviderConfig> {
  const r = await fetch(
    `${API}/tenant/ai/providers/${encodeURIComponent(providerName)}/validate${tenantQuery(tenantSlug)}`,
    {
      method: "POST"}
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
  portfolio_project_id: number | null;
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
  portfolio_project_id: number | null;
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

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const r = await fetch(`${API}/telemetry/summary`, { credentials: "include"});
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
  llm_invocation: {
    ok_total: number;
    degraded_total: number;
  };
};

export async function fetchObservabilitySummary(windowSeconds = 300): Promise<ObservabilitySummary> {
  const r = await fetch(`${API}/telemetry/observability/summary?window_seconds=${windowSeconds}`, { credentials: "include"});
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

export async function fetchDecisionLifecycle(): Promise<DecisionLifecycle> {
  const r = await fetch(`${API}/telemetry/decision-lifecycle`, { credentials: "include"});
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

export async function fetchIntelligenceIncidents(limit = 10): Promise<IntelligenceIncident[]> {
  const r = await fetch(`${API}/intelligence/incidents?limit=${limit}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<IntelligenceIncident[]>;
}

export async function fetchConsensusSummary(): Promise<ConsensusSummary> {
  const r = await fetch(`${API}/intelligence/consensus/summary`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ConsensusSummary>;
}

export async function fetchExecutiveSummaries(limit = 5): Promise<ExecutiveSummary[]> {
  const r = await fetch(`${API}/intelligence/executive-summaries?limit=${limit}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ExecutiveSummary[]>;
}

export async function fetchReleaseGovernance(): Promise<ReleaseGovernance> {
  const r = await fetch(`${API}/intelligence/release-governance`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ReleaseGovernance>;
}

export async function runRarIteration(incidentId: number): Promise<RARIteration> {
  const r = await fetch(`${API}/intelligence/incidents/${incidentId}/rar`, { credentials: "include",
    method: "POST"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<RARIteration>;
}

export async function runGovernanceWorkflow(
  workflowType: string,
  incidentId?: number
): Promise<WorkflowRun> {
  const q = typeof incidentId === "number" ? `?incident_id=${incidentId}` : "";
  const r = await fetch(`${API}/intelligence/workflows/${encodeURIComponent(workflowType)}${q}`, { credentials: "include",
    method: "POST"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<WorkflowRun>;
}

export async function fetchWorkflowRuns(workflowType?: string): Promise<WorkflowRun[]> {
  const q = workflowType ? `?workflow_type=${encodeURIComponent(workflowType)}` : "";
  const r = await fetch(`${API}/intelligence/workflows${q}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<WorkflowRun[]>;
}

export async function createGovernanceRun(
  body: { prompt: string; prompt_id?: string | null; portfolio_project_id?: number | null },
  tenantSlug?: string | null
): Promise<GovernanceRunV1> {
  const r = await fetch(`${API}/governance/runs${tenantQuery(tenantSlug)}`, { credentials: "include",
    method: "POST",
    headers: { "Content-Type": "application/json"},
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceRunV1>;
}

export async function fetchGovernanceRun(runId: number): Promise<GovernanceRunV1> {
  const r = await fetch(`${API}/governance/runs/${runId}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceRunV1>;
}

export type GovernanceShareLink = {
  url: string;
  expires_at: string;
};

export async function createGovernanceRunShareLink(
  runId: number,
  body?: { expires_in_hours?: number }
): Promise<GovernanceShareLink> {
  const r = await fetch(`${API}/governance/runs/${runId}/share-link`, { credentials: "include",
    method: "POST",
    headers: { "Content-Type": "application/json"},
    body: JSON.stringify({ expires_in_hours: body?.expires_in_hours ?? 168 })});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceShareLink>;
}

export async function fetchGovernanceRuns(
  params?: { status?: string; limit?: number; offset?: number; query?: string; portfolio_project_id?: number }
): Promise<GovernanceRunV1[]> {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.limit) search.set("limit", String(params.limit));
  if (typeof params?.offset === "number") search.set("offset", String(params.offset));
  if (params?.query) search.set("prompt_contains", params.query);
  if (typeof params?.portfolio_project_id === "number") {
    search.set("portfolio_project_id", String(params.portfolio_project_id));
  }
  const suffix = search.toString() ? `?${search.toString()}` : "";
  const r = await fetch(`${API}/governance/runs${suffix}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceRunV1[]>;
}

export async function createCase(
  body: {
    title: string;
    run_id?: number | null;
    owner_user_id?: number | null;
    portfolio_project_id?: number | null;
  },
  tenantSlug?: string | null
): Promise<GovernanceCase> {
  const r = await fetch(`${API}/governance/cases${tenantQuery(tenantSlug)}`, { credentials: "include",
    method: "POST",
    headers: { "Content-Type": "application/json"},
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceCase>;
}

export async function fetchCases(limit = 100): Promise<GovernanceCase[]> {
  const r = await fetch(`${API}/governance/cases?limit=${limit}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceCase[]>;
}

export async function fetchCasesAdvanced(
  params?: { status?: string; limit?: number; offset?: number; query?: string; portfolio_project_id?: number }
): Promise<GovernanceCase[]> {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (typeof params?.limit === "number") q.set("limit", String(params.limit));
  if (typeof params?.offset === "number") q.set("offset", String(params.offset));
  if (params?.query) q.set("title_contains", params.query);
  if (typeof params?.portfolio_project_id === "number") {
    q.set("portfolio_project_id", String(params.portfolio_project_id));
  }
  const suffix = q.toString() ? `?${q.toString()}` : "";
  const r = await fetch(`${API}/governance/cases${suffix}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceCase[]>;
}

export async function updateCase(
  caseId: number,
  body: {
    status?: string;
    owner_user_id?: number | null;
    latest_run_id?: number | null;
    portfolio_project_id?: number | null;
  }
): Promise<GovernanceCase> {
  const r = await fetch(`${API}/governance/cases/${caseId}`, { credentials: "include",
    method: "PATCH",
    headers: { "Content-Type": "application/json"},
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<GovernanceCase>;
}

export async function createDecision(
  caseId: number,
  body: { run_id?: number | null; recommended_action?: string | null; rationale?: string | null }
): Promise<Decision> {
  const r = await fetch(`${API}/governance/cases/${caseId}/decisions`, { credentials: "include",
    method: "POST",
    headers: { "Content-Type": "application/json"},
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<Decision>;
}

export async function approveDecision(
  decisionId: number,
  body: { final_action: string; rationale?: string | null }
): Promise<Decision> {
  const r = await fetch(`${API}/governance/decisions/${decisionId}/approve`, { credentials: "include",
    method: "POST",
    headers: { "Content-Type": "application/json"},
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<Decision>;
}

export async function fetchAuditEvents(
  params?: { area?: string; severity?: string; limit?: number }
): Promise<AuditEvent[]> {
  const q = new URLSearchParams();
  if (params?.area) q.set("area", params.area);
  if (params?.severity) q.set("severity", params.severity);
  if (typeof params?.limit === "number") q.set("limit", String(params.limit));
  const suffix = q.toString() ? `?${q.toString()}` : "";
  const r = await fetch(`${API}/governance/audit-events${suffix}`, { credentials: "include"});
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
  params?: { connector?: string; run_id?: number; portfolio_project_id?: number; limit?: number; offset?: number }
): Promise<EvidenceRow[]> {
  const q = new URLSearchParams();
  if (params?.connector) q.set("connector", params.connector);
  if (typeof params?.run_id === "number") q.set("run_id", String(params.run_id));
  if (typeof params?.portfolio_project_id === "number") {
    q.set("portfolio_project_id", String(params.portfolio_project_id));
  }
  if (typeof params?.limit === "number") q.set("limit", String(params.limit));
  if (typeof params?.offset === "number") q.set("offset", String(params.offset));
  const suffix = q.toString() ? `?${q.toString()}` : "";
  const r = await fetch(`${API}/governance/evidence${suffix}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<EvidenceRow[]>;
}

export async function acknowledgeAlert(eventId: number): Promise<AuditEvent> {
  const r = await fetch(`${API}/governance/audit-events/${eventId}/acknowledge`, { credentials: "include",
    method: "POST"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<AuditEvent>;
}

export async function fetchRunSummaryReport(
  format: "json" | "csv",
  limit = 200,
  status?: string,
  portfolioProjectId?: number
): Promise<{ count: number; items: Record<string, unknown>[] } | Blob> {
  const q = new URLSearchParams();
  q.set("format", format);
  q.set("limit", String(limit));
  if (status) q.set("status", status);
  if (typeof portfolioProjectId === "number") q.set("portfolio_project_id", String(portfolioProjectId));
  const r = await fetch(`${API}/reports/runs/summary?${q.toString()}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  if (format === "csv") return r.blob();
  return r.json();
}

export async function fetchSingleRunExport(
  runId: number,
  format: "json" | "csv"
): Promise<
  | {
      format_version: number;
      summary_columns: Record<string, unknown>;
      executive_bundle: Record<string, unknown>;
    }
  | Blob
> {
  const q = new URLSearchParams();
  q.set("format", format);
  const r = await fetch(`${API}/reports/runs/${runId}/export?${q.toString()}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  if (format === "csv") return r.blob();
  return r.json();
}

export async function fetchAuditExport(
  format: "json" | "csv",
  area?: string
): Promise<{ count: number; items: Record<string, unknown>[] } | Blob> {
  const q = new URLSearchParams();
  q.set("format", format);
  if (area) q.set("area", area);
  const r = await fetch(`${API}/reports/audit-events?${q.toString()}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  if (format === "csv") return r.blob();
  return r.json();
}

export type PortfolioProject = {
  id: number;
  tenant_id: number | null;
  key: string;
  name: string;
  owner: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type PortfolioRelease = {
  id: number;
  tenant_id: number | null;
  project_id: number;
  version: string;
  target_date: string | null;
  status: string;
  release_decision: string | null;
  decision_confidence: number | null;
  consensus_score: number | null;
  risk_level: string | null;
  run_id: number | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ExecutivePortfolioReport = {
  projects_total: number;
  active_projects: number;
  releases_total: number;
  releases_planned: number;
  releases_approved: number;
  releases_blocked: number;
  avg_confidence: number;
  avg_consensus: number;
  high_risk_open: number;
  project_breakdown: {
    project_id: number;
    project_key: string;
    project_name: string;
    releases_total: number;
    go_count: number;
    hold_count: number;
    avg_confidence: number;
  }[];
};

export type PortfolioOperationsContext = {
  runs_total: number;
  runs_24h: number;
  runs_success_24h: number;
  cases_open: number;
  cases_total: number;
  alerts_24h: number;
  evidence_snapshots_total: number;
  decisions_total: number;
  decisions_approved: number;
  portfolio_releases_total: number;
  portfolio_releases_linked_to_run: number;
};

export async function fetchPortfolioProjects(): Promise<PortfolioProject[]> {
  const r = await fetch(`${API}/portfolio/projects`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<PortfolioProject[]>;
}

export async function createPortfolioProject(
  body: { key: string; name: string; owner?: string | null; status?: string }
): Promise<PortfolioProject> {
  const r = await fetch(`${API}/portfolio/projects`, { credentials: "include",
    method: "POST",
    headers: { "Content-Type": "application/json"},
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<PortfolioProject>;
}

export async function fetchPortfolioReleases(): Promise<PortfolioRelease[]> {
  const r = await fetch(`${API}/portfolio/releases`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<PortfolioRelease[]>;
}

export async function createPortfolioRelease(
  body: {
    project_id: number;
    version: string;
    status?: string;
    target_date?: string | null;
    release_decision?: string | null;
    decision_confidence?: number | null;
    consensus_score?: number | null;
    risk_level?: string | null;
    run_id?: number | null;
  }
): Promise<PortfolioRelease> {
  const r = await fetch(`${API}/portfolio/releases`, { credentials: "include",
    method: "POST",
    headers: { "Content-Type": "application/json"},
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<PortfolioRelease>;
}

export async function fetchExecutivePortfolioReport(): Promise<ExecutivePortfolioReport> {
  const r = await fetch(`${API}/portfolio/reports/executive`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<ExecutivePortfolioReport>;
}

export async function fetchPortfolioOperationsContext(): Promise<PortfolioOperationsContext> {
  const r = await fetch(`${API}/portfolio/reports/operations-context`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<PortfolioOperationsContext>;
}

export type NotificationTemplate = {
  subject: string;
  body: string;
};

export type TenantNotificationConfig = {
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_username: string | null;
  smtp_password_configured: boolean;
  smtp_from_email: string | null;
  use_tls: boolean;
  use_ssl: boolean;
  notifications_enabled: boolean;
  slack_webhook_configured: boolean;
  governance_notify_on_run_complete: boolean;
  governance_run_notify_emails: string[];
  templates: Record<string, NotificationTemplate>;
  last_test_ok: boolean | null;
  last_test_error: string | null;
  last_tested_at: string | null;
};

export async function fetchNotificationConfig(tenantSlug?: string | null): Promise<TenantNotificationConfig> {
  const r = await fetch(`${API}/tenant/notifications${tenantQuery(tenantSlug)}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<TenantNotificationConfig>;
}

export async function saveNotificationConfig(
  body: {
    smtp_host?: string | null;
    smtp_port?: number | null;
    smtp_username?: string | null;
    smtp_password?: string | null;
    smtp_from_email?: string | null;
    use_tls?: boolean;
    use_ssl?: boolean;
    notifications_enabled?: boolean;
    slack_incoming_webhook?: string | null;
    clear_slack_incoming_webhook?: boolean;
    governance_notify_on_run_complete?: boolean;
    governance_run_notify_emails?: string[];
    templates?: Record<string, NotificationTemplate>;
  },
  tenantSlug?: string | null
): Promise<TenantNotificationConfig> {
  const r = await fetch(`${API}/tenant/notifications${tenantQuery(tenantSlug)}`, { credentials: "include",
    method: "PUT",
    headers: { "Content-Type": "application/json"},
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<TenantNotificationConfig>;
}

export async function testNotificationConfig(
  body: { to_email?: string | null },
  tenantSlug?: string | null
): Promise<{ ok: boolean; message: string }> {
  const r = await fetch(`${API}/tenant/notifications/test${tenantQuery(tenantSlug)}`, { credentials: "include",
    method: "POST",
    headers: { "Content-Type": "application/json"},
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<{ ok: boolean; message: string }>;
}

export type AdminUser = {
  id: number;
  email: string;
  is_admin: boolean;
  is_superadmin: boolean;
  is_active: boolean;
  tenant_id: number | null;
  role_names: string[];
};

export async function fetchRbacUsers(tenantSlug?: string | null): Promise<AdminUser[]> {
  const q = tenantSlug ? `?tenant_slug=${encodeURIComponent(tenantSlug)}` : "";
  const r = await fetch(`${API}/rbac/users${q}`, { credentials: "include"});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json() as Promise<AdminUser[]>;
}

export async function createRbacUser(
  body: { email: string; role_name: string; is_active?: boolean },
  tenantSlug?: string | null
): Promise<{ id: number; email: string; role_name: string; tenant_id: number; delivery_status: string; temporary_password: string | null }> {
  const q = tenantSlug ? `?tenant_slug=${encodeURIComponent(tenantSlug)}` : "";
  const r = await fetch(`${API}/rbac/users${q}`, { credentials: "include",
    method: "POST",
    headers: { "Content-Type": "application/json"},
    body: JSON.stringify(body)});
  if (!r.ok) throw new Error(await parseError(r));
  return r.json();
}
