import { Link } from "react-router-dom";
import type { RecommendationView } from "../../lib/governancePresentation";

type AIRecommendationCardProps = {
  recommendation: RecommendationView;
};

export function AIRecommendationCard({ recommendation }: AIRecommendationCardProps) {
  const runQ = recommendation.runId ? `?run_id=${recommendation.runId}` : "";

  return (
    <article className="gov-recommendation">
      <div className="gov-recommendation-head">
        <div className="gov-recommendation-badges">
          {recommendation.badges.map((b) => (
            <span key={b.label} className={`gov-pill gov-pill--${b.variant === "success" ? "healthy" : "info"}`}>
              {b.label}
            </span>
          ))}
        </div>
        <span className="gov-recommendation-conf">CONFIDENCE {recommendation.confidenceLabel}</span>
      </div>
      <h2 className="gov-recommendation-title">{recommendation.headline}</h2>
      <p className="gov-recommendation-body">{recommendation.narrative}</p>
      <div className="gov-recommendation-metrics">
        <div>
          <span className="gov-metric-label">Consensus Score</span>
          <strong>{recommendation.consensusScore != null ? recommendation.consensusScore.toFixed(2) : "—"}</strong>
          <span className="gov-metric-hint">Inter-agent agreement</span>
        </div>
        <div>
          <span className="gov-metric-label">RAR Triggered</span>
          <strong>{recommendation.rarTriggered ? "Yes" : "No"}</strong>
          <span className="gov-metric-hint">Re-grounded on conflict</span>
        </div>
        <div>
          <span className="gov-metric-label">Utility Score</span>
          <strong>{recommendation.utilityScore != null ? recommendation.utilityScore.toFixed(2) : "—"}</strong>
          <span className="gov-metric-hint">Risk-weighted decision</span>
        </div>
      </div>
      <div className="gov-recommendation-actions">
        <Link
          to={recommendation.runId ? `/app/cases?run_id=${recommendation.runId}` : "/app/cases"}
          className="btn btn-primary btn-sm"
        >
          Review Decision →
        </Link>
        <Link to={`/app/evidence${runQ}`} className="btn btn-ghost btn-sm">
          View Evidence
        </Link>
        <Link to={`/app/runs${runQ}`} className="btn btn-ghost btn-sm">
          Agent Reasoning
        </Link>
      </div>
    </article>
  );
}
