import { useEffect, useState } from "react";
import { convertLeadToTenant, fetchLeads, type AccessLead } from "../api";

type WorkspaceLeadsPageProps = {
  };

export function WorkspaceLeadsPage({}: WorkspaceLeadsPageProps) {
  const [rows, setRows] = useState<AccessLead[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchLeads()
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load leads"))
      .finally(() => setLoading(false));
  }, []);

  const convert = async (row: AccessLead) => {
    try {
      const slug = row.organization_name
        .toLowerCase()
        .replace(/[^a-z0-9- ]/g, "")
        .trim()
        .replace(/\s+/g, "-")
        .replace(/^-+/, "")
        .slice(0, 48);
      const out = await convertLeadToTenant(row.id, {
        tenant_name: row.organization_name,
        tenant_slug: slug || `tenant-${row.id}`,
      });
      setRows((prev) => prev.map((x) => (x.id === row.id ? out : x)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to convert lead");
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <h1>Leads</h1>
          <span>Request access submissions and tenant provisioning</span>
        </div>
      </header>
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      <div className="card">
        {loading ? <p style={{ color: "var(--muted)" }}>Loading leads…</p> : null}
        {!loading ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Organization</th>
                  <th>Contact</th>
                  <th>Email</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>{r.organization_name}</td>
                    <td>{r.contact_name}</td>
                    <td className="mono">{r.work_email}</td>
                    <td>
                      <span className={`status-chip ${r.status === "converted" ? "succeeded" : "queued"}`}>{r.status}</span>
                    </td>
                    <td>
                      <button className="btn btn-ghost" type="button" disabled={r.status === "converted"} onClick={() => convert(r)}>
                        {r.status === "converted" ? "Converted" : "Create tenant"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </div>
  );
}
