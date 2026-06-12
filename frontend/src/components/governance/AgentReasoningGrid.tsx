import { useState } from "react";
import type { AgentCardView } from "../../lib/governancePresentation";
import { linkifyEvidenceText } from "../../lib/evidenceLinks";

type AgentReasoningGridProps = {
  agents: AgentCardView[];
  rarLoops?: number;
};

export function AgentReasoningGrid({ agents, rarLoops = 0 }: AgentReasoningGridProps) {
  const [expanded, setExpanded] = useState<string | null>(null);
  return (
    <div className="gov-agent-grid">
      {agents.map((agent) => (
        <article
          key={agent.id}
          className={`gov-agent-card ${agent.isOrchestrator ? "gov-agent-card--orchestrator" : ""} ${expanded === agent.id ? "gov-agent-card--open" : ""}`}
        >
          <div className="gov-agent-card-head">
            <div>
              <h3>{agent.name}</h3>
              <p>{agent.domain}</p>
            </div>
            <div className="gov-agent-card-badges">
              {agent.toolCallLabel ? (
                <span className="gov-pill gov-pill--neutral" title="Tools invoked in this run">
                  {agent.toolCallLabel}
                </span>
              ) : null}
              {agent.transport === "mcp" ? (
                <span className="gov-pill gov-pill--mcp" title="Evidence fetched via MCP transport">
                  MCP
                </span>
              ) : null}
              {agent.isOrchestrator ? <span className="gov-pill gov-pill--info">Orchestrator</span> : null}
            </div>
          </div>
          <p className="gov-agent-claim-label">Claim</p>
          <p className="gov-agent-claim">{agent.claim}</p>
          <p className="gov-agent-claim-label">Confidence</p>
          <div className="gov-confidence-bar gov-confidence-bar--agent">
            <span style={{ width: `${Math.round(agent.confidence * 100)}%` }} />
          </div>
          <span className="gov-agent-conf-pct">{Math.round(agent.confidence * 100)}%</span>
          <p className="gov-agent-claim-label">Evidence</p>
          <p className="gov-agent-evidence">{linkifyEvidenceText(agent.evidence[0] ?? "")}</p>
          <button
            type="button"
            className="btn btn-ghost btn-sm gov-agent-drawer-toggle"
            onClick={() => setExpanded((id) => (id === agent.id ? null : agent.id))}
          >
            {expanded === agent.id ? "Hide details" : "Show evidence & signals"}
          </button>
          {expanded === agent.id ? (
            <div className="gov-agent-drawer">
              <ul>
                {agent.evidence.map((line) => (
                  <li key={line}>{linkifyEvidenceText(line)}</li>
                ))}
              </ul>
              {agent.isOrchestrator && rarLoops > 0 ? (
                <p className="gov-agent-rar">RAR loops: {rarLoops}</p>
              ) : null}
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}
