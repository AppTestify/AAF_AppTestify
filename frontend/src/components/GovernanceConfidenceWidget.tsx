import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchConsensusSummary } from "../api";

export function GovernanceConfidenceWidget() {
  const [pct, setPct] = useState<number | null>(null);

  useEffect(() => {
    fetchConsensusSummary()
      .then((s) => setPct(Math.round(s.avg_consensus_score * 100)))
      .catch(() => setPct(null));
  }, []);

  return (
    <Link to="/app/dashboard" className="workspace-gov-widget">
      <span className="workspace-gov-widget-label">Governance</span>
      <span className="workspace-gov-widget-value">{pct != null ? `${pct}%` : "—"}</span>
      <span className="workspace-gov-widget-hint">Confidence index</span>
    </Link>
  );
}
