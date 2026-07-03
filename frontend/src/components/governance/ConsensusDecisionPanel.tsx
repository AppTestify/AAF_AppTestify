import { useState } from "react";
import type { DecisionFraming } from "../../lib/governancePresentation";
import { formatActionLabel, isHoldReleaseAction } from "../../lib/governancePresentation";
import type { DecisionAction, GovernanceRunResult } from "../../api";
import { executeGovernanceRunActions } from "../../api";

type ConsensusDecisionPanelProps = {
  result: GovernanceRunResult;
  framing: DecisionFraming;
  runId?: number;
  canExecute?: boolean;
};

export function ConsensusDecisionPanel({ result, framing, runId, canExecute = false }: ConsensusDecisionPanelProps) {
  const orch = framing.orchestration;
  const consensus = orch?.consensus_score ?? result.consensus?.consensus_score;
  const utility = orch?.utility_score ?? result.utility?.global_utility ?? result.utility?.utility_score;
  const rawAction = orch?.recommended_action ?? result.utility?.recommended_action;
  const action = formatActionLabel(rawAction);
  const holdRelease = isHoldReleaseAction(rawAction);
  const rarTriggered = result.rar?.rar_triggered ?? orch?.rar_triggered;
  const [executing, setExecuting] = useState(false);
  const [actions, setActions] = useState<DecisionAction[] | null>(null);
  const [execError, setExecError] = useState<string | null>(null);

  const actionable = canExecute && runId != null && (holdRelease || rawAction === "patch_block_release");

  const handleExecute = async () => {
    if (!runId) return;
    setExecuting(true);
    setExecError(null);
    try {
      const rows = await executeGovernanceRunActions(runId);
      setActions(rows);
    } catch (err) {
      setExecError(err instanceof Error ? err.message : "Execution failed");
    } finally {
      setExecuting(false);
    }
  };

  return (
    <section className="gov-consensus-panel">
      <div className="gov-consensus-head">
        <h3>Consensus & Decision</h3>
        <span className={`gov-pill ${holdRelease ? "gov-pill--hold-release" : "gov-pill--healthy"}`}>
          {holdRelease ? "Release Blocked" : "Final Decision Ready"}
        </span>
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
          <div className={`gov-final-decision-card ${holdRelease ? "gov-final-decision-card--hold-release" : ""}`}>
            <span>Final Decision</span>
            <strong>{action}</strong>
            <small>{holdRelease ? "Phase 3 hold — resolve blockers before release" : "High confidence"}</small>
          </div>
        </div>
        {actionable ? (
          <div className="gov-automation-actions" style={{ marginTop: "1rem" }}>
            <button type="button" className="btn btn-primary" disabled={executing} onClick={handleExecute}>
              {executing ? "Executing…" : "Execute decision (Jira + hold workflow)"}
            </button>
            <p className="muted" style={{ marginTop: "0.5rem", fontSize: "0.875rem" }}>
              Creates a Jira blocker and triggers the hold-release workflow when automation is enabled in Settings.
            </p>
            {execError ? (
              <div className="alert alert-error" role="alert">
                {execError}
              </div>
            ) : null}
            {actions && actions.length > 0 ? (
              <ul className="gov-action-log" style={{ marginTop: "0.75rem", fontSize: "0.875rem" }}>
                {actions.map((a) => (
                  <li key={a.id}>
                    <strong>{a.action_type}</strong> — {a.state}
                    {a.result_json && typeof a.result_json.key === "string" ? ` (${a.result_json.key})` : ""}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </div>
      <div className="gov-rar-explainer">
        <strong>RAR (Retrieval-Augmented Reasoning)</strong> re-checks evidence when signals are incomplete or
        conflicting, ensuring the final recommendation is grounded in the most reliable data available.
      </div>
    </section>
  );
}
