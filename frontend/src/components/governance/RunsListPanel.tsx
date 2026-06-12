import type { GovernanceRunV1 } from "../../api";
import { formatRelativeTime } from "../../lib/governancePresentation";

type RunsListPanelProps = {
  runs: GovernanceRunV1[];
  selectedRunId: number | null;
  onSelect: (runId: number) => void;
  loading?: boolean;
};

function runTimeLabel(run: GovernanceRunV1): string {
  if (run.status === "running" || run.status === "queued") {
    const start = run.started_at ?? run.created_at;
    const secs = Math.max(0, Math.floor((Date.now() - new Date(start).getTime()) / 1000));
    return `${secs}s`;
  }
  const ref = run.finished_at ?? run.created_at;
  return formatRelativeTime(ref);
}

export function RunsListPanel({ runs, selectedRunId, onSelect, loading }: RunsListPanelProps) {
  if (loading) return <div className="runs-list-skeleton" aria-busy="true" />;
  if (!runs.length) return <p className="runs-list-empty">No runs found for the current filters.</p>;

  return (
    <ul className="runs-list runs-list--panel">
      {runs.map((run) => {
        const isLive = run.status === "running" || run.status === "queued";
        const isSelected = selectedRunId === run.id;
        return (
          <li key={run.id}>
            <button
              type="button"
              className={`runs-list-item runs-list-item--${run.status} ${isLive ? "runs-list-item--live" : ""} ${
                isSelected ? "runs-list-item--selected" : ""
              }`}
              onClick={() => onSelect(run.id)}
            >
              <div className="runs-list-item-main">
                <span className="runs-list-prompt">{run.prompt}</span>
                <span className="runs-list-meta">
                  <span className={`status-chip status-chip--inline ${run.status}`}>
                    {isLive ? <span className="status-pulse-dot" aria-hidden="true" /> : null}
                    {run.status}
                  </span>
                  <span>· {runTimeLabel(run)}</span>
                  <span className="mono">· #{run.id}</span>
                </span>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
