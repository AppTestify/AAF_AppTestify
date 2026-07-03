import { useEffect, useState } from "react";
import { createTenant, fetchTenants, type TenantRow } from "../api";

type WorkspaceTenantsPageProps = {
  };

export function WorkspaceTenantsPage({}: WorkspaceTenantsPageProps) {
  const [rows, setRows] = useState<TenantRow[]>([]);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchTenants();
      setRows(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tenants");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  const onCreate = async () => {
    if (!name.trim() || !slug.trim()) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await createTenant({ name: name.trim(), slug: slug.trim() });
      setName("");
      setSlug("");
      setMessage("Tenant created successfully.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create tenant");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header workspace-page-head">
        <div className="brand">
          <h1>Tenant management</h1>
          <span>Platform owner control center for multi-tenant workspace provisioning.</span>
        </div>
      </header>
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      {message ? <div className="alert alert-success">{message}</div> : null}
      <div className="workspace-split">
        <div className="card">
          <h2>Create tenant</h2>
          <p className="workspace-card-subtitle">Provision a new organization tenant and make it available immediately.</p>
          <div className="form-row">
            <label htmlFor="tenant-name">Organization name</label>
            <input
              id="tenant-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Acme Corp"
              disabled={saving}
            />
          </div>
          <div className="form-row">
            <label htmlFor="tenant-slug">Tenant slug</label>
            <input
              id="tenant-slug"
              className="mono"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="acme"
              disabled={saving}
            />
          </div>
          <button className="btn btn-primary" type="button" onClick={onCreate} disabled={saving || !name.trim() || !slug.trim()}>
            {saving ? "Creating…" : "Create tenant"}
          </button>
        </div>
        <div className="card">
          <h2>Platform tenant registry</h2>
          <p className="workspace-card-subtitle">Active tenants and user footprint across your platform.</p>
          {loading ? <p className="field-hint">Loading tenants…</p> : null}
          {!loading ? (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Slug</th>
                    <th>Name</th>
                    <th>Users</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((t) => (
                    <tr key={t.id}>
                      <td className="mono">{t.slug}</td>
                      <td>{t.name}</td>
                      <td>{t.user_count}</td>
                      <td>
                        <span className={`status-chip ${t.is_active ? "succeeded" : "failed"}`}>
                          {t.is_active ? "active" : "inactive"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
