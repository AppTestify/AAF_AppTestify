import { Link } from "react-router-dom";
import type { DashboardSummary } from "../../api";
import { formatRelativeTime } from "../../lib/governancePresentation";

type RecentRunsListProps = {
  runs?: DashboardSummary["recent_runs"];
};

export function RecentRunsList({ runs = [] }: RecentRunsListProps) {
  return (
    <article className="card recent-runs-card">
      <h3>Recent runs</h3>
      <p className="workspace-meta">Click a row to open run detail with run_id in context.</p>
      <ul className="runs-list">
        {runs.length === 0 ? (
          <li className="runs-list-empty">No governance runs in the last 24 hours.</li>
        ) : (
          runs.map((run) => (
            <li key={run.id}>
              <Link
                to={`/app/runs?run_id=${run.id}`}
                className={`runs-list-item runs-list-item--${run.status} ${
                  run.status === "running" || run.status === "queued" ? "runs-list-item--live" : ""
                }`}
              >
                <div className="runs-list-item-main">
                  <span className="runs-list-prompt">{run.prompt}</span>
                  <span className="runs-list-meta">
                    <span className={`status-chip status-chip--inline ${run.status}`}>
                      {(run.status === "running" || run.status === "queued") && (
                        <span className="status-pulse-dot" aria-hidden="true" />
                      )}
                      {run.status}
                    </span>
                    <span>· {formatRelativeTime(run.created_at)}</span>
                    <span className="mono">· #{run.id}</span>
                  </span>
                </div>
              </Link>
            </li>
          ))
        )}
      </ul>
    </article>
  );
}
