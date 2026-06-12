import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSignupStatus, fetchToolRegistry, type ToolRegistryResponse } from "../api";
import { WORKSPACE_FEATURES } from "../marketing/content";
import { ToolRegistryTable } from "../components/governance/ToolRegistryTable";
import { MarketingLayout } from "./MarketingLayout";
import "../App.css";

export function CapabilitiesPage() {
  const [signupOpen, setSignupOpen] = useState<boolean | null>(null);
  const [registry, setRegistry] = useState<ToolRegistryResponse | null>(null);
  const [showFullRegistry, setShowFullRegistry] = useState(false);
  useEffect(() => {
    fetchSignupStatus()
      .then((s) => setSignupOpen(s.tenant_signup_enabled))
      .catch(() => setSignupOpen(false));
  }, []);

  useEffect(() => {
    fetchToolRegistry(showFullRegistry ? { status: "all" } : { status: "shipped" })
      .then(setRegistry)
      .catch(() => setRegistry(null));
  }, [showFullRegistry]);

  return (
    <MarketingLayout signupOpen={signupOpen}>
      <section className="marketing-subhero">
        <div className="marketing-subhero-inner">
          <p className="section-eyebrow">Capabilities</p>
          <h1 className="section-title">What Casantris does today</h1>
          <p className="section-lead">
            Four domain agents, {registry?.meta.shipped_count ?? "24+"} shipped tools (sim or live), weighted confidence
            scoring, and a full governance workspace — not generic AI chat wrapped around dashboards.
          </p>
        </div>
      </section>

      <section className="section subpage-band">
        <p className="section-eyebrow">Agent tool layer</p>
        <h2 className="section-title">Every agent calls real tools — in parallel</h2>
        <p className="section-lead" style={{ marginTop: "0.75rem" }}>
          Scroll the registry for API endpoints, MCP mappings, return signals, and PM scenarios per tool.
        </p>
        <label className="tool-registry-toggle" style={{ display: "inline-flex", marginTop: "1rem" }}>
          <input
            type="checkbox"
            checked={showFullRegistry}
            onChange={(e) => setShowFullRegistry(e.target.checked)}
          />
          Full registry including roadmap
        </label>
        {registry ? (
          <div style={{ marginTop: "1rem" }}>
            <ToolRegistryTable data={registry} defaultStatus={showFullRegistry ? "all" : "shipped"} readOnly />
          </div>
        ) : (
          <p className="field-hint" style={{ marginTop: "1rem" }}>
            Loading tool registry…
          </p>
        )}
      </section>

      <section className="section subpage-band subpage-band-dark">
        <p className="section-eyebrow">Scoring & reasoning</p>
        <h2 className="section-title">Confidence you can explain to a PM</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Weighted confidence</h3>
            <p>Each tool returns a 0–1 risk signal. Agent confidence = Σ(weight × signal) with staleness down-weighting.</p>
          </article>
          <article className="feature-card">
            <h3>FinOps reasoning core</h3>
            <p>Claim generator, Ci efficiency scorer, and evidence packager produce PM-readable cost narratives.</p>
          </article>
          <article className="feature-card">
            <h3>DevSecOps binary gates</h3>
            <p>A single critical CVE or detected secret forces confidence ≥ 0.90 — a hard ship blocker.</p>
          </article>
          <article className="feature-card">
            <h3>PM blocker logic</h3>
            <p>Five or more sprint blockers trigger action-level confidence regardless of velocity ratio.</p>
          </article>
          <article className="feature-card">
            <h3>Global utility U</h3>
            <p>U = 0.4·P + 0.3·Ci + 0.3·R surfaces perf, cost-efficiency, and security risk in one index.</p>
          </article>
          <article className="feature-card">
            <h3>Explainability (XI)</h3>
            <p>Heuristic explainability index plus LLM executive narrative for stakeholder communication.</p>
          </article>
        </div>
      </section>

      <section className="section subpage-band">
        <p className="section-eyebrow">Workspace</p>
        <h2 className="section-title">Governance operations beyond the agent run</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          {WORKSPACE_FEATURES.map((f) => (
            <article key={f.title} className="feature-card">
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="subpage-cta">
        <div className="subpage-cta-inner">
          <div className="subpage-cta-copy">
            <strong>Map these capabilities to your release governance model.</strong>
            <span>Walk through the pipeline or start a pilot tenant.</span>
          </div>
          <div className="subpage-cta-actions">
            <Link to="/how-it-works" className="btn btn-ghost">
              How it works
            </Link>
            <Link to="/request-access" className="btn btn-primary">
              Request access
            </Link>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
