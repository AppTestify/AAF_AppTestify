import type { ConnectorSummaryCard } from "../../lib/governancePresentation";

type EvidenceSourceCardsProps = {
  cards: ConnectorSummaryCard[];
};

export function EvidenceSourceCards({ cards }: EvidenceSourceCardsProps) {
  return (
    <div className="gov-evidence-sources">
      {cards.map((card) => (
        <article key={card.id} className="gov-source-card">
          <div className="gov-source-card-head">
            <div>
              <h3>{card.title}</h3>
              <p>{card.subtitle}</p>
            </div>
            <span className={`gov-pill gov-pill--${card.badgeVariant === "action" ? "high" : card.badgeVariant === "watch" ? "medium" : "healthy"}`}>
              {card.badge}
            </span>
          </div>
          <ul className="gov-source-metrics">
            {card.metrics.map((m) => (
              <li key={m.label}>
                {m.dot ? <span className={`gov-dot gov-dot--${m.dot}`} aria-hidden="true" /> : null}
                <span className="gov-source-metric-label">{m.label}</span>
                <strong>{m.value}</strong>
              </li>
            ))}
          </ul>
        </article>
      ))}
    </div>
  );
}
