import type { TimelineRow } from "../../lib/governancePresentation";
import { EvidenceDetailCell } from "../../lib/evidenceLinks";

type EvidenceTimelineTableProps = {
  rows: TimelineRow[];
  refreshedLabel?: string;
  jiraBaseUrl?: string | null;
};

export function EvidenceTimelineTable({ rows, refreshedLabel, jiraBaseUrl }: EvidenceTimelineTableProps) {
  return (
    <article className="gov-evidence-timeline card">
      <div className="gov-timeline-head">
        <div>
          <h3>Evidence Timeline</h3>
          <p>Recently retrieved signals informing the current decision</p>
        </div>
        {refreshedLabel ? <span className="gov-timeline-refreshed">{refreshedLabel}</span> : null}
      </div>
      <div className="table-wrap">
        <table className="data-table gov-evidence-timeline-table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Signal</th>
              <th>Detail</th>
              <th>Captured</th>
              <th>Severity</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="table-empty">
                  No evidence signals yet. Run a governance check to populate the timeline.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.source}</td>
                  <td>{row.signal}</td>
                  <td>
                    <EvidenceDetailCell detail={row.detail} record={row.record} jiraBaseUrl={jiraBaseUrl} />
                  </td>
                  <td>{row.captured}</td>
                  <td>
                    <span className={`gov-pill gov-pill--${row.severity === "high" ? "high" : row.severity === "medium" ? "medium" : "info"}`}>
                      {row.severity === "high" ? "High" : row.severity === "medium" ? "Medium" : "Info"}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </article>
  );
}
