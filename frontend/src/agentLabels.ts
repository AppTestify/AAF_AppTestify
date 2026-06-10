/** Friendly labels for pipeline agent_id and intelligence agent_name values. */

const LABELS: Record<string, string> = {
  devops: "DevOps",
  project_management: "PM",
  finops: "FinOps",
  devsecops: "DevSecOps",
  DevOpsAgent: "DevOps",
  PMAgent: "PM",
  FinOpsAgent: "FinOps",
  DevSecOpsAgent: "DevSecOps",
  SREAgent: "PM (legacy)",
};

export function formatAgentLabel(agentIdOrName: string): string {
  return LABELS[agentIdOrName] ?? agentIdOrName;
}

export type AgentFinding = {
  agent_name: string;
  domain: string;
  severity: string;
  confidence: number;
  summary: string;
  evidence_json?: Record<string, unknown>;
};

export function parseIncidentFindings(evidenceJson: Record<string, unknown> | undefined): AgentFinding[] {
  const raw = evidenceJson?.findings;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((row): row is Record<string, unknown> => row != null && typeof row === "object")
    .map((row) => ({
      agent_name: String(row.agent_name ?? "Unknown"),
      domain: String(row.domain ?? "governance"),
      severity: String(row.severity ?? "info"),
      confidence: Number(row.confidence ?? 0),
      summary: String(row.summary ?? ""),
      evidence_json:
        row.evidence_json && typeof row.evidence_json === "object"
          ? (row.evidence_json as Record<string, unknown>)
          : undefined,
    }));
}
