import { useState, useEffect } from "react";
import type { AgentCardView } from "../../lib/governancePresentation";
import { linkifyEvidenceText } from "../../lib/evidenceLinks";
import { SegmentedTabs } from "../ui/SegmentedTabs";

type AgentReasoningGridProps = {
  agents: AgentCardView[];
  rarLoops?: number;
};

export function AgentReasoningGrid({ agents, rarLoops = 0 }: AgentReasoningGridProps) {
  const [activeId, setActiveId] = useState<string>("");

  useEffect(() => {
    if (!activeId && agents.length > 0) {
      setActiveId(agents[0].id);
    }
  }, [agents, activeId]);

  if (agents.length === 0) return null;

  const tabs = agents.map(a => ({
    id: a.id,
    label: a.name
  }));

  const activeAgent = agents.find(a => a.id === activeId) || agents[0];

  return (
    <div className="gov-agent-tabs-container" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <SegmentedTabs tabs={tabs} activeId={activeId || tabs[0].id} onChange={setActiveId} />
      
      <article className={`gov-agent-card ${activeAgent.isOrchestrator ? "gov-agent-card--orchestrator" : ""}`}>
        <div className="gov-agent-card-head">
          <div>
            <h3>{activeAgent.name}</h3>
            <p>{activeAgent.domain}</p>
          </div>
          <div className="gov-agent-card-badges">
            {activeAgent.toolCallLabel ? (
              <span className="gov-pill gov-pill--neutral" title="Tools invoked in this run">
                {activeAgent.toolCallLabel}
              </span>
            ) : null}
            {activeAgent.transport === "mcp" ? (
              <span className="gov-pill gov-pill--mcp" title="Evidence fetched via MCP transport">
                MCP
              </span>
            ) : null}
            {activeAgent.isOrchestrator ? <span className="gov-pill gov-pill--info">Orchestrator</span> : null}
          </div>
        </div>
        <p className="gov-agent-claim-label">Claim</p>
        <p className="gov-agent-claim">{activeAgent.claim}</p>
        <p className="gov-agent-claim-label">Confidence</p>
        <div className="gov-confidence-bar gov-confidence-bar--agent">
          <span style={{ width: `${Math.round(activeAgent.confidence * 100)}%` }} />
        </div>
        <span className="gov-agent-conf-pct">{Math.round(activeAgent.confidence * 100)}%</span>
        
        <p className="gov-agent-claim-label">Evidence & Signals</p>
        <div className="gov-agent-drawer" style={{ display: 'block', marginTop: '0.5rem', background: 'transparent', padding: 0, border: 'none' }}>
          <ul>
            {activeAgent.evidence.map((line) => (
              <li key={line}>{linkifyEvidenceText(line)}</li>
            ))}
          </ul>
          {activeAgent.isOrchestrator && rarLoops > 0 ? (
            <p className="gov-agent-rar" style={{ marginTop: '1rem' }}>RAR loops: {rarLoops}</p>
          ) : null}
        </div>
      </article>
    </div>
  );
}

