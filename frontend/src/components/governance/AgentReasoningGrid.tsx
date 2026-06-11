import type { AgentCardView } from "../../lib/governancePresentation";

type AgentReasoningGridProps = {
  agents: AgentCardView[];
};

export function AgentReasoningGrid({ agents }: AgentReasoningGridProps) {
  return (
    <div className="gov-agent-grid">
      {agents.map((agent) => (
        <article
          key={agent.id}
          className={`gov-agent-card ${agent.isOrchestrator ? "gov-agent-card--orchestrator" : ""}`}
        >
          <div className="gov-agent-card-head">
            <div>
              <h3>{agent.name}</h3>
              <p>{agent.domain}</p>
            </div>
            {agent.isOrchestrator ? <span className="gov-pill gov-pill--info">Orchestrator</span> : null}
          </div>
          <p className="gov-agent-claim-label">Claim</p>
          <p className="gov-agent-claim">{agent.claim}</p>
          <p className="gov-agent-claim-label">Confidence</p>
          <div className="gov-confidence-bar gov-confidence-bar--agent">
            <span style={{ width: `${Math.round(agent.confidence * 100)}%` }} />
          </div>
          <span className="gov-agent-conf-pct">{Math.round(agent.confidence * 100)}%</span>
          <p className="gov-agent-claim-label">Evidence</p>
          <p className="gov-agent-evidence">{agent.evidence[0]}</p>
        </article>
      ))}
    </div>
  );
}
