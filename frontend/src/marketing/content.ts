/** Shared marketing copy aligned to current product capabilities. */

export const AGENTS = [
  {
    id: "devops",
    name: "DevOps",
    tagline: "Release branch safety",
    tools: ["CI status", "Deploy history", "Rollback detection", "Branch protection"],
    signals: "ci_pass_rate, rollback_24h, reviews_met",
    weight: "Weighted confidence with 4h staleness penalty",
  },
  {
    id: "pm",
    name: "PM",
    tagline: "Sprint delivery health",
    tools: ["Sprint status", "Blocker count", "Open defects", "Velocity risk"],
    signals: "sprint_done_pct, blocked_count, velocity_ratio",
    weight: "5+ blockers trigger action regardless of velocity",
  },
  {
    id: "finops",
    name: "FinOps",
    tagline: "Cloud cost efficiency",
    tools: ["Spend trend", "Budget pace", "Scaling anomalies", "Unit cost", "RI coverage"],
    signals: "wow_delta_pct, Ci score, orphan_scale_flag",
    weight: "6h staleness · scaling + spend spike correlation boost",
  },
  {
    id: "devsecops",
    name: "DevSecOps",
    tagline: "Ship-safe security posture",
    tools: ["CVE scan", "Secret scanning", "Policy violations", "Dependency audit"],
    signals: "critical_cve, secrets_detected, violation_count",
    weight: "Critical CVE or secret forces ≥0.90 confidence",
  },
] as const;

export const INTEGRATIONS = [
  { name: "GitHub", detail: "Actions, deployments, branch protection, Dependabot" },
  { name: "Jira", detail: "Agile sprints, blockers, defects, velocity" },
  { name: "AWS", detail: "Cost Explorer, Budgets, Auto Scaling, CloudWatch" },
  { name: "Azure DevOps", detail: "Builds, releases, policy signals" },
  { name: "FinOps file", detail: "JSON/CSV cost export fallback" },
] as const;

export const PIPELINE_STEPS = [
  {
    step: "1",
    title: "Connect evidence sources",
    body: "Enable GitHub, Jira, AWS, Azure, or FinOps file connectors per tenant. Validate credentials before live runs.",
  },
  {
    step: "2",
    title: "Run four domain agents in parallel",
    body: "17 spec-aligned tools fetch live or sim signals. Each agent produces a claim, confidence score, and PM-readable evidence.",
  },
  {
    step: "3",
    title: "Reach consensus with RAR",
    body: "Low consensus triggers Re-Grounded Agentic Reasoning — stale tools refresh and agents re-score until tau is met.",
  },
  {
    step: "4",
    title: "Score utility and explain",
    body: "Global U = 0.4·P + 0.3·Ci + 0.3·R drives action selection. Explainability index (XI) and executive narrative close the loop.",
  },
] as const;

export const WORKSPACE_FEATURES = [
  { title: "Governance runs", desc: "Sync or queued runs with agent opinions, evidence tabs, and utility indices." },
  { title: "Cases & approvals", desc: "Formal case lifecycle with recommendations, approvers, and audit events." },
  { title: "Evidence snapshots", desc: "Connector payloads preserved per run for triage and compliance." },
  { title: "Incident intelligence", desc: "Cross-agent findings synthesized into correlated incidents with PMAgent delivery signals." },
  { title: "Workflow governance", desc: "Release, cost spike, security, and post-incident review workflows." },
  { title: "Reports & exports", desc: "JSON, CSV, executive summaries, and signed share links for leadership." },
] as const;

export const TECH_STACK = [
  "GitHub",
  "Jira",
  "AWS",
  "Azure",
  "FastAPI",
  "React",
  "PostgreSQL",
  "OpenAI",
  "boto3",
  "Python",
] as const;
