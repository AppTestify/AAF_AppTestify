import type { DecisionFraming } from "../../lib/governancePresentation";
import { formatActionLabel } from "../../lib/governancePresentation";
import type { GovernanceRunResult } from "../../api";

type ConsensusDecisionPanelProps = {
  result: GovernanceRunResult;
  framing: DecisionFraming;
};

export function ConsensusDecisionPanel({ result, framing }: ConsensusDecisionPanelProps) {
  const orch = framing.orchestration;
  const consensus = orch?.consensus_score ?? result.consensus?.consensus_score;
  const utility = orch?.utility_score ?? result.utility?.global_utility ?? result.utility?.utility_score;
  const action = formatActionLabel(orch?.recommended_action ?? result.utility?.recommended_action);
  const rarTriggered = result.rar?.rar_triggered ?? orch?.rar_triggered;

  return (
    <section className="gov-consensus-panel">
      <div className="gov-consensus-head">
        <h3>Consensus & Decision</h3>
        <span className="gov-pill gov-pill--healthy">Final Decision Ready</span>
      </div>
      <div className="gov-consensus-body">
        <div className="gov-consensus-metrics">
          <div className="gov-consensus-metric">
            <span>Consensus Score</span>
            <strong>{consensus != null ? consensus.toFixed(2) : "—"}</strong>
            <small>Agents in agreement</small>
          </div>
          <div className="gov-consensus-metric">
            <span>RAR Re-grounding</span>
            <strong>{rarTriggered ? "Triggered" : "Not needed"}</strong>
            <small>{rarTriggered ? "Conflict resolved" : "Signals aligned"}</small>
          </div>
          <div className="gov-consensus-metric">
            <span>Utility Score</span>
            <strong>{utility != null ? utility.toFixed(2) : "—"}</strong>
            <small>Risk-weighted</small>
          </div>
          <div className="gov-final-decision-card">
            <span>Final Decision</span>
            <strong>{action}</strong>
            <small>High confidence</small>
          </div>
        </div>
      </div>
      <div className="gov-rar-explainer">
        <strong>RAR (Retrieval-Augmented Reasoning)</strong> re-checks evidence when signals are incomplete or
        conflicting, ensuring the final recommendation is grounded in the most reliable data available.
      </div>
    </section>
  );
}
