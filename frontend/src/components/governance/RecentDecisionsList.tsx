import type { RecentDecisionItem } from "../../lib/governancePresentation";

type RecentDecisionsListProps = {
  items: RecentDecisionItem[];
};

export function RecentDecisionsList({ items }: RecentDecisionsListProps) {
  return (
    <article className="gov-recent-decisions">
      <h3>Recent Decisions</h3>
      <p className="gov-recent-sub">Last 24 hours</p>
      <ul className="gov-recent-list">
        {items.length === 0 ? (
          <li className="gov-recent-empty">No recent governance activity yet.</li>
        ) : (
          items.map((item) => (
            <li key={item.id} className="gov-recent-item">
              <span className={`gov-recent-dot gov-recent-dot--${item.variant}`} aria-hidden="true" />
              <div>
                <strong>{item.title}</strong>
                <span>{item.subtitle}</span>
              </div>
              <time>{item.time}</time>
            </li>
          ))
        )}
      </ul>
    </article>
  );
}
