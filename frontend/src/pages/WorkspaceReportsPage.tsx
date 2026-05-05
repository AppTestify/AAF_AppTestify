import { useState } from "react";
import { fetchAuditExport, fetchRunSummaryReport } from "../api";

type WorkspaceReportsPageProps = {
  token: string;
};

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function WorkspaceReportsPage({ token }: WorkspaceReportsPageProps) {
  const [output, setOutput] = useState<string>("");
  const [toast, setToast] = useState<string>("");
  const [error, setError] = useState<string>("");

  const notify = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 2200);
  };

  const exportRunsJson = async () => {
    try {
      setError("");
      const data = (await fetchRunSummaryReport(token, "json")) as { count: number; items: Record<string, unknown>[] };
      setOutput(JSON.stringify(data, null, 2));
      notify(`Loaded ${data.count} run summary rows`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run summary failed");
    }
  };

  const exportRunsCsv = async () => {
    try {
      setError("");
      const blob = (await fetchRunSummaryReport(token, "csv")) as Blob;
      downloadBlob(blob, "governance_run_summary.csv");
      notify("Run summary CSV downloaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "CSV export failed");
    }
  };

  const exportAuditJson = async () => {
    try {
      setError("");
      const data = (await fetchAuditExport(token, "json")) as { count: number; items: Record<string, unknown>[] };
      setOutput(JSON.stringify(data, null, 2));
      notify(`Loaded ${data.count} audit rows`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Audit export failed");
    }
  };

  const exportAuditCsv = async () => {
    try {
      setError("");
      const blob = (await fetchAuditExport(token, "csv")) as Blob;
      downloadBlob(blob, "audit_events.csv");
      notify("Audit CSV downloaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Audit CSV export failed");
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <h1>Reports</h1>
          <span>Export governance run summaries and audit events</span>
        </div>
      </header>
      {toast ? <div className="alert alert-success">{toast}</div> : null}
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      <div className="card">
        <h2>Run summary</h2>
        <div className="actions">
          <button className="btn btn-ghost" type="button" onClick={exportRunsJson}>
            View JSON
          </button>
          <button className="btn btn-primary" type="button" onClick={exportRunsCsv}>
            Download CSV
          </button>
        </div>
      </div>
      <div className="card">
        <h2>Audit events</h2>
        <div className="actions">
          <button className="btn btn-ghost" type="button" onClick={exportAuditJson}>
            View JSON
          </button>
          <button className="btn btn-primary" type="button" onClick={exportAuditCsv}>
            Download CSV
          </button>
        </div>
      </div>
      {output ? (
        <div className="card">
          <h2>Preview</h2>
          <pre style={{ maxHeight: 420, overflow: "auto" }}>{output}</pre>
        </div>
      ) : null}
    </div>
  );
}
