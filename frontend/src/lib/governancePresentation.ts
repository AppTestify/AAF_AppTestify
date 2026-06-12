import type {
  AgentOpinion,
  ConsensusSummary,
  DashboardSummary,
  EvidenceRecord,
  EvidenceRow,
  GovernanceCase,
  GovernanceRunResult,
  GovernanceRunV1,
  ReleaseGovernance,
} from "../api";
import { formatAgentLabel } from "../agentLabels";

export type DecisionFraming = {
  orchestration?: {
    consensus_score?: number;
    rar_triggered?: boolean;
    rar_loops?: number;
    consensus_before?: number;
    consensus_after?: number;
    recommended_action?: string;
    utility_score?: number;
    global_utility?: number;
    perf_index?: number;
    cost_index?: number;
    risk_index?: number;
    xi_score?: number;
    reground_notes?: string[];
  };
  findings_synthesis?: {
    consensus_score?: number;
    confidence?: number;
    conflict_detected?: boolean;
  };
  primary_recommendation_source?: string;
  intent_category?: string;
  agents_activated?: string[];
};

export type ParsedRunContext = {
  run: GovernanceRunV1;
  result: GovernanceRunResult;
  framing: DecisionFraming;
};

export function parseRunResult(json: Record<string, unknown> | null | undefined): GovernanceRunResult | null {
  if (!json || typeof json !== "object") return null;
  if (!Array.isArray(json.agent_opinions) && !json.utility && !json.consensus) return null;
  return json as unknown as GovernanceRunResult;
}

export function parseGovernanceRunResult(run: GovernanceRunV1): ParsedRunContext | null {
  const result = parseRunResult(run.result_json);
  if (!result) return null;
  const framing = (result.decision_framing ?? {}) as DecisionFraming;
  return { run, result, framing };
}

export function formatActionLabel(action: string | null | undefined): string {
  if (!action) return "Pending review";
  const map: Record<string, string> = {
    patch_block_release: "Hold Release",
    rollback: "Rollback",
    mitigate_monitor: "Mitigate & Monitor",
    scale_adjust: "Scale Adjust",
    observe: "Observe",
    investigate: "Investigate",
    approved: "Approved",
  };
  return map[action] ?? action.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return "Yesterday";
  return `${days}d ago`;
}

export type RiskCardView = {
  id: string;
  title: string;
  status: string;
  detail: string;
  variant: "action" | "watch" | "healthy" | "neutral";
};

export function deriveRiskCards(
  releaseGov: ReleaseGovernance | null,
  consensus: ConsensusSummary | null,
  parsed: ParsedRunContext | null
): RiskCardView[] {
  const utility = parsed?.result.utility;
  const perf = utility?.perf_index ?? 0.5;
  const cost = utility?.cost_index ?? 0.5;
  const risk = utility?.risk_index ?? 0.5;
  const consensusScore = parsed?.result.consensus?.consensus_score ?? consensus?.avg_consensus_score ?? releaseGov?.consensus_score ?? 0;

  const releaseStatus =
    releaseGov?.risk_level === "high" || releaseGov?.decision === "block"
      ? { status: "At Risk", variant: "action" as const, detail: releaseGov?.reason?.slice(0, 48) || "Blockers detected" }
      : releaseGov?.risk_level === "medium"
        ? { status: "Watch", variant: "watch" as const, detail: releaseGov?.reason?.slice(0, 48) || "Review recommended" }
        : { status: "Ready", variant: "healthy" as const, detail: releaseGov?.reason?.slice(0, 48) || "Consensus aligned" };

  const deliveryStatus =
    perf < 0.45 || risk > 0.7
      ? { status: "High", variant: "action" as const, detail: "Sprint or security pressure elevated" }
      : perf < 0.65
        ? { status: "Medium", variant: "watch" as const, detail: "Some delivery friction" }
        : { status: "Low", variant: "healthy" as const, detail: "Delivery on track" };

  const costStatus =
    cost < 0.45
      ? { status: "High", variant: "action" as const, detail: "Cost efficiency below threshold" }
      : cost < 0.65
        ? { status: "Medium", variant: "watch" as const, detail: "Spend trend warrants review" }
        : { status: "Low", variant: "healthy" as const, detail: "Cost posture healthy" };

  const govPct = Math.round(consensusScore * 100);
  const govStatus =
    consensusScore >= 0.7
      ? { status: `${govPct}%`, variant: "healthy" as const, detail: "Consensus aligned" }
      : consensusScore >= 0.45
        ? { status: `${govPct}%`, variant: "watch" as const, detail: "Partial agent agreement" }
        : { status: `${govPct}%`, variant: "action" as const, detail: "Low consensus — RAR may apply" };

  return [
    { id: "release", title: "Release Readiness", ...releaseStatus },
    { id: "delivery", title: "Delivery Risk", ...deliveryStatus },
    { id: "cost", title: "Cloud Cost Risk", ...costStatus },
    { id: "governance", title: "Governance Confidence", ...govStatus },
  ];
}

export type RecommendationView = {
  headline: string;
  narrative: string;
  consensusScore: number | null;
  rarTriggered: boolean;
  utilityScore: number | null;
  confidenceLabel: string;
  runId: number | null;
  badges: { label: string; variant: "primary" | "success" }[];
};

export function deriveRecommendation(parsed: ParsedRunContext | null, releaseGov: ReleaseGovernance | null): RecommendationView | null {
  if (!parsed && !releaseGov) return null;
  const { result, framing, run } = parsed ?? { result: null, framing: {}, run: null };
  const orch = framing.orchestration;
  const action = orch?.recommended_action ?? result?.utility?.recommended_action ?? releaseGov?.decision ?? "observe";
  const headline = formatActionLabel(action);
  const narrative =
    result?.pm_view?.summary_markdown?.split("\n")[0]?.replace(/^#+\s*/, "") ??
    releaseGov?.reason ??
    "Review agent evidence and connector signals before promoting to production.";
  const consensusScore = orch?.consensus_score ?? result?.consensus?.consensus_score ?? releaseGov?.consensus_score ?? null;
  const utilityScore = orch?.utility_score ?? result?.utility?.global_utility ?? result?.utility?.utility_score ?? null;
  const rarTriggered = result?.rar?.rar_triggered ?? orch?.rar_triggered ?? false;
  const conf = consensusScore ?? 0;
  const confidenceLabel = conf >= 0.75 ? "High" : conf >= 0.5 ? "Medium" : "Low";

  return {
    headline,
    narrative: narrative.slice(0, 220),
    consensusScore,
    rarTriggered,
    utilityScore,
    confidenceLabel,
    runId: run?.id ?? null,
    badges: [
      { label: "AI Recommendation", variant: "primary" },
      { label: consensusScore != null && consensusScore >= 0.65 ? "Consensus Aligned" : "Review Needed", variant: consensusScore != null && consensusScore >= 0.65 ? "success" : "primary" },
    ],
  };
}

export type RecentDecisionItem = {
  id: string;
  title: string;
  subtitle: string;
  time: string;
  variant: "hold" | "approve" | "alert";
};

export function deriveRecentDecisions(
  summary: DashboardSummary | null,
  cases: GovernanceCase[]
): RecentDecisionItem[] {
  const items: RecentDecisionItem[] = [];
  for (const r of summary?.recent_runs ?? []) {
    const action = r.status === "succeeded" ? "Governance run" : r.status;
    items.push({
      id: `run-${r.id}`,
      title: action,
      subtitle: r.prompt.slice(0, 42) + (r.prompt.length > 42 ? "…" : ""),
      time: formatRelativeTime(r.created_at),
      variant: r.status === "failed" ? "alert" : "hold",
    });
  }
  for (const c of cases.filter((x) => x.status === "approved" || x.status === "in_review").slice(0, 4)) {
    items.push({
      id: `case-${c.id}`,
      title: c.status === "approved" ? "Approved decision" : "Case in review",
      subtitle: c.title,
      time: formatRelativeTime(c.updated_at),
      variant: c.status === "approved" ? "approve" : "hold",
    });
  }
  return items.slice(0, 6);
}

export type FlowStep = {
  id: string;
  label: string;
  detail?: string;
  active?: boolean;
  completed?: boolean;
};

export function deriveDecisionFlow(parsed: ParsedRunContext | null, runStatus?: string | null): FlowStep[] {
  if (!parsed) {
    return [
      { id: "prompt", label: "PM Prompt", detail: "Ask Casantris AI" },
      { id: "github", label: "GitHub", detail: "Evidence" },
      { id: "jira", label: "Jira", detail: "Evidence" },
      { id: "finops", label: "FinOps", detail: "Evidence" },
      { id: "secops", label: "SecOps", detail: "Security" },
      { id: "agents", label: "AI Agents", detail: "Reasoning" },
      { id: "consensus", label: "Consensus", detail: "—" },
      { id: "brief", label: "Brief", detail: "Executive" },
      { id: "decision", label: "Decision", detail: "Pending", active: true },
    ];
  }
  const { result, framing } = parsed;
  const action = formatActionLabel(framing.orchestration?.recommended_action ?? result.utility?.recommended_action);
  const score = framing.orchestration?.consensus_score ?? result.consensus?.consensus_score;
  const status = runStatus ?? parsed.run.status;
  const running = status === "running" || status === "queued";
  const done = status === "succeeded";
  const secopsActive = (framing.agents_activated ?? result.agents_activated ?? []).includes("devsecops");
  const secopsOpinion = result.agent_opinions?.find((o) => o.agent_id === "devsecops");
  return [
    { id: "prompt", label: "PM Prompt", detail: result.prompt.slice(0, 24) + (result.prompt.length > 24 ? "…" : ""), completed: true },
    { id: "github", label: "GitHub", detail: "Evidence", completed: done || !running },
    { id: "jira", label: "Jira", detail: "Evidence", completed: done || !running },
    { id: "finops", label: "FinOps", detail: "Evidence", completed: done || !running },
    {
      id: "secops",
      label: "SecOps",
      detail: secopsActive ? (secopsOpinion ? "Active" : "Queued") : "Skipped",
      completed: done && secopsActive,
      active: running && secopsActive,
    },
    {
      id: "agents",
      label: "AI Agents",
      detail: `${result.agent_opinions?.length ?? framing.agents_activated?.length ?? 3} agents`,
      active: running,
      completed: done,
    },
    { id: "consensus", label: "Consensus", detail: score != null ? score.toFixed(2) : "—", completed: done, active: running },
    { id: "brief", label: "Brief", detail: result.governance_brief ? "Ready" : "Pending", completed: done, active: false },
    { id: "decision", label: "Decision", detail: action, active: done, completed: done },
  ];
}

export function isLiveTrace(runStatus: string | null | undefined, finishedAt: string | null): boolean {
  if (runStatus === "running" || runStatus === "queued") return true;
  if (!finishedAt) return false;
  return Date.now() - new Date(finishedAt).getTime() < 30 * 60 * 1000;
}

export type ConnectorSummaryCard = {
  id: string;
  title: string;
  subtitle: string;
  badge: string;
  badgeVariant: "action" | "watch" | "healthy";
  metrics: { label: string; value: string; dot?: "red" | "yellow" | "green" }[];
};

function numSignal(signals: Record<string, unknown> | undefined, key: string, fallback = "—"): string {
  const v = signals?.[key];
  if (v == null) return fallback;
  return String(v);
}

export function deriveConnectorSummaries(
  parsed: ParsedRunContext | null,
  connectorHealth: DashboardSummary["connector_health"] | null
): ConnectorSummaryCard[] {
  const signals = (parsed?.run.result_json?.integration_signals ?? {}) as Record<string, Record<string, unknown>>;
  const github = signals.github ?? {};
  const jira = signals.jira ?? {};
  const aws = signals.aws ?? signals.finops ?? {};

  const ghFailed = Number(github.failed_checks ?? github.ci_failures ?? 0);
  const ghBadge = ghFailed > 0 ? "Risk Detected" : "Healthy";
  const jiraBlockers = Number(jira.blocked_count ?? jira.blockers ?? 0);
  const jiraBadge = jiraBlockers >= 3 ? "Delivery Risk" : jiraBlockers > 0 ? "Watch" : "On Track";
  const spendDelta = String(aws.wow_delta_pct ?? aws.spend_increase_pct ?? "—");
  const finBadge = Number(spendDelta) > 20 ? "Cost Watch" : "Stable";

  const secopsOpinion = parsed?.result.agent_opinions?.find((o) => o.agent_id === "devsecops");
  const secSignals = secopsOpinion?.raw_signals ?? {};
  const cveCount = Number((secSignals.scan_cves as Record<string, unknown> | undefined)?.critical_count ?? secSignals.cve_count ?? 0);
  const secBadge = cveCount > 0 ? "Security Risk" : secopsOpinion ? "Reviewed" : "Not activated";

  const ghOk = connectorHealth?.find((c) => c.connector_name === "github")?.last_validation_ok;

  return [
    {
      id: "github",
      title: "GitHub Evidence",
      subtitle: "Source control & CI/CD",
      badge: ghBadge,
      badgeVariant: ghFailed > 0 ? "action" : "healthy",
      metrics: [
        { label: "Failed workflow checks", value: String(ghFailed), dot: ghFailed > 0 ? "red" : "green" },
        { label: "Open pull requests", value: numSignal(github, "open_prs", "0") },
        { label: "Release branch status", value: ghFailed > 0 ? "Blocked" : "Clear" },
        { label: "Connector health", value: ghOk === false ? "Invalid" : ghOk ? "Valid" : "—" },
      ],
    },
    {
      id: "jira",
      title: "JIRA Evidence",
      subtitle: "Delivery & sprint health",
      badge: jiraBadge,
      badgeVariant: jiraBlockers >= 3 ? "action" : jiraBlockers > 0 ? "watch" : "healthy",
      metrics: [
        { label: "Blocked stories", value: String(jiraBlockers), dot: jiraBlockers > 0 ? "red" : "green" },
        { label: "High-priority defects", value: numSignal(jira, "open_defects", "0"), dot: "yellow" },
        { label: "Sprint completion", value: numSignal(jira, "sprint_done_pct", "—") + (jira.sprint_done_pct != null ? "%" : "") },
        { label: "Release blockers", value: numSignal(jira, "blocked_count", "0"), dot: jiraBlockers > 0 ? "red" : undefined },
      ],
    },
    {
      id: "finops",
      title: "FinOps Evidence",
      subtitle: "Cloud spend & budget",
      badge: finBadge,
      badgeVariant: Number(spendDelta) > 20 ? "watch" : "healthy",
      metrics: [
        { label: "Cloud spend change", value: spendDelta !== "—" ? `+${spendDelta}%` : "—" },
        { label: "Budget variance", value: numSignal(aws, "budget_variance_pct", "—") },
        { label: "Top cost driver", value: numSignal(aws, "top_cost_driver", "App compute") },
        { label: "Cost trend", value: Number(spendDelta) > 15 ? "Rising" : "Stable" },
      ],
    },
    {
      id: "secops",
      title: "SecOps Evidence",
      subtitle: "CVE, secrets & policy",
      badge: secBadge,
      badgeVariant: cveCount > 0 ? "action" : secopsOpinion ? "healthy" : "watch",
      metrics: [
        { label: "Critical CVEs", value: String(cveCount), dot: cveCount > 0 ? "red" : "green" },
        { label: "Agent confidence", value: secopsOpinion ? secopsOpinion.confidence.toFixed(2) : "—" },
        { label: "Policy violations", value: numSignal(secSignals as Record<string, unknown>, "policy_violations", "0") },
        { label: "Status", value: secopsOpinion ? "Activated" : "Skipped for prompt" },
      ],
    },
  ];
}

export type TimelineRow = {
  id: string;
  source: string;
  signal: string;
  detail: string;
  captured: string;
  severity: "high" | "medium" | "info";
};

export function deriveEvidenceTimeline(
  rows: EvidenceRow[],
  normalized: EvidenceRecord[]
): TimelineRow[] {
  const fromRows: TimelineRow[] = rows.map((r) => ({
    id: `row-${r.id}`,
    source: r.connector_name,
    signal: "Connector snapshot",
    detail: `Run #${r.run_id} payload`,
    captured: formatRelativeTime(r.created_at),
    severity: "info",
  }));

  const fromNorm: TimelineRow[] = normalized.map((e, i) => ({
    id: `norm-${i}`,
    source: e.source,
    signal: e.kind,
    detail: e.summary,
    captured: "This run",
    severity: e.severity >= 0.75 ? "high" : e.severity >= 0.45 ? "medium" : "info",
  }));

  return [...fromNorm, ...fromRows].slice(0, 12);
}

export type AgentCardView = {
  id: string;
  name: string;
  domain: string;
  claim: string;
  confidence: number;
  evidence: string[];
  isOrchestrator?: boolean;
};

const AGENT_DOMAINS: Record<string, string> = {
  devops: "Source control & deployment",
  pm: "Sprint health & delivery",
  project_management: "Sprint health & delivery",
  finops: "Cloud cost & budget",
  devsecops: "Security posture",
  orchestrator: "Final synthesis",
};

export function deriveAgentGrid(
  opinions: AgentOpinion[],
  framing: DecisionFraming
): AgentCardView[] {
  const agents = opinions.map((o) => ({
    id: o.agent_id,
    name: formatAgentLabel(o.agent_id, o.display_id),
    domain: AGENT_DOMAINS[o.agent_id] ?? "Governance domain",
    claim: o.claim,
    confidence: o.confidence,
    evidence: o.evidence?.length ? o.evidence : [o.claim],
  }));

  const orch = framing.orchestration;
  if (orch?.recommended_action) {
    agents.push({
      id: "orchestrator",
      name: "Governance Orchestrator",
      domain: AGENT_DOMAINS.orchestrator,
      claim: formatActionLabel(orch.recommended_action),
      confidence: orch.consensus_score ?? 0.82,
      evidence: orch.reground_notes?.length
        ? orch.reground_notes
        : ["Cross-agent consensus with RAR re-grounding applied"],
      isOrchestrator: true,
    });
  }

  return agents;
}

export type AskRecommendationColumns = {
  deliveryRisk: string;
  costRisk: string;
  securityRisk: string;
  confidence: string;
  recommendation: string;
  why: string;
  impact: string;
  nextStep: string;
};

export function deriveAskColumns(result: GovernanceRunResult): AskRecommendationColumns {
  const utility = result.utility;
  const perf = utility?.perf_index ?? 0.5;
  const cost = utility?.cost_index ?? 0.5;
  const conf = result.consensus?.consensus_score ?? 0.5;

  const deliveryRisk = perf < 0.45 ? "High" : perf < 0.65 ? "Medium" : "Low";
  const costRisk = cost < 0.45 ? "High" : cost < 0.65 ? "Medium" : "Low";
  const secOpinion = result.agent_opinions?.find((o) => o.agent_id === "devsecops");
  const securityRisk =
    !secOpinion && !(result.agents_activated ?? []).includes("devsecops")
      ? "N/A"
      : secOpinion && secOpinion.confidence >= 0.65
        ? "Elevated"
        : "Watch";
  const confidence = conf >= 0.75 ? "High" : conf >= 0.5 ? "Medium" : "Low";

  const action = formatActionLabel(utility?.recommended_action);
  const recommendation =
    result.pm_view?.title ??
    `Recommendation: ${action} until blockers and checks are resolved.`;

  const pmText = result.pm_view?.summary_markdown ?? result.explanation ?? "";
  const lines = pmText.split("\n").filter((l) => l.trim());

  return {
    deliveryRisk,
    costRisk,
    securityRisk,
    confidence,
    recommendation,
    why: lines[0]?.replace(/^[-*#]+\s*/, "") || "Multiple agent signals indicate elevated delivery risk.",
    impact: lines[1]?.replace(/^[-*#]+\s*/, "") || "A forced release risks customer-facing regressions and SLA exposure.",
    nextStep: lines[2]?.replace(/^[-*#]+\s*/, "") || "Resolve blockers, re-run checks, and re-evaluate within 24 hours.",
  };
}

export async function loadLatestSucceededRun(
  fetchRuns: (p: { status: string; limit: number }) => Promise<GovernanceRunV1[]>,
  fetchRun: (id: number) => Promise<GovernanceRunV1>
): Promise<ParsedRunContext | null> {
  const runs = await fetchRuns({ status: "succeeded", limit: 1 });
  if (!runs.length) return null;
  const full = await fetchRun(runs[0].id);
  return parseGovernanceRunResult(full);
}
