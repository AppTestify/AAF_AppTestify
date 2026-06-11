import type { RiskCardView } from "../../lib/governancePresentation";

type RiskMetricCardProps = {
  cards: RiskCardView[];
};

export function RiskMetricCard({ cards }: RiskMetricCardProps) {
  return (
    <div className="gov-risk-row">
      {cards.map((card) => (
        <article key={card.id} className={`gov-risk-card gov-risk-card--${card.variant}`}>
          <div className="gov-risk-card-head">
            <h3>{card.title}</h3>
            <span className={`gov-pill gov-pill--${card.variant === "action" ? "high" : card.variant === "watch" ? "medium" : "healthy"}`}>
              {card.variant === "action" ? "Action" : card.variant === "watch" ? "Watch" : "Healthy"}
            </span>
          </div>
          <p className="gov-risk-card-status">{card.status}</p>
          <p className="gov-risk-card-detail">{card.detail}</p>
          {card.id === "governance" ? (
            <div className="gov-confidence-bar" aria-hidden="true">
              <span style={{ width: `${parseInt(card.status, 10) || 0}%` }} />
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}
