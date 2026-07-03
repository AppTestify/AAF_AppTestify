import { formatAgentLabel, parseIncidentFindings } from "../api";
import type { IntelligenceIncident } from "../api";

type Props = {
  incident: IntelligenceIncident;
  compact?: boolean;
};

export function IncidentFindingsPanel({ incident, compact = false }: Props) {
  const findings = parseIncidentFindings(incident.evidence_json);
  if (!findings.length) {
    return compact ? null : (
      <p className="field-hint" style={{ margin: "0.5rem 0 0" }}>
        No per-agent findings attached to this incident.
      </p>
    );
  }

  return (
    <ul className={`list-plain ${compact ? "incident-findings-compact" : "incident-findings-list"}`}>
      {findings.map((f, idx) => (
        <li key={`${f.agent_name}-${idx}`}>
          <strong>{formatAgentLabel(f.agent_name)}</strong>
          <span className={`status-chip ${f.severity === "critical" ? "failed" : "running"}`} style={{ marginLeft: "0.5rem" }}>
            {f.severity}
          </span>
          <span className="field-hint" style={{ marginLeft: "0.5rem" }}>
            conf {f.confidence.toFixed(2)}
          </span>
          {!compact ? <p style={{ margin: "0.25rem 0 0" }}>{f.summary}</p> : <span> — {f.summary}</span>}
        </li>
      ))}
    </ul>
  );
}
