import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchToolRegistry, type ToolRegistryResponse } from "../api";
import { ToolRegistryTable } from "../components/governance/ToolRegistryTable";

export function WorkspaceToolRegistryPage() {
  const [data, setData] = useState<ToolRegistryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchToolRegistry(showAll ? { status: "all" } : { status: "shipped" })
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [showAll]);

  return (
    <div className="workspace-page">
      <div className="workspace-section-intro">
        <div>
          <p className="gov-hub-eyebrow">AI Config</p>
          <h1>AgileOps tool registry</h1>
          <p>
            Canonical registry of agent tools — methods, API endpoints, MCP mappings, return signals, and PM scenarios.
            Shipped tools are wired into governance runs and the tool scope guardrail.
          </p>
        </div>
        <label className="tool-registry-toggle">
          <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} />
          Full registry (pending + roadmap)
        </label>
      </div>

      <p className="field-hint">
        Configure connectors in{" "}
        <Link to="/app/settings">Settings</Link> or{" "}
        <Link to="/app/ai-config">AI Providers</Link>.{" "}
        <Link to="/capabilities">Marketing capabilities</Link> uses the same registry.
      </p>

      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      {loading ? <div className="card">Loading tool registry…</div> : null}
      {!loading && data ? <ToolRegistryTable data={data} defaultStatus={showAll ? "all" : "shipped"} /> : null}
    </div>
  );
}
