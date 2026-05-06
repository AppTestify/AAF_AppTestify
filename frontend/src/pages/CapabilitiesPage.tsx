import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSignupStatus } from "../api";
import { MarketingLayout } from "./MarketingLayout";
import "../App.css";

export function CapabilitiesPage() {
  const [signupOpen, setSignupOpen] = useState<boolean | null>(null);
  useEffect(() => {
    fetchSignupStatus()
      .then((s) => setSignupOpen(s.tenant_signup_enabled))
      .catch(() => setSignupOpen(false));
  }, []);

  return (
    <MarketingLayout signupOpen={signupOpen}>
      <section className="marketing-subhero">
        <div className="marketing-subhero-inner">
          <p className="section-eyebrow">Capabilities</p>
          <h1 className="section-title">Capabilities designed for governance confidence</h1>
          <p className="section-lead">A complete capability stack for trust-first operational decisioning and governance control.</p>
        </div>
      </section>

      <section className="section subpage-band">
        <p className="section-eyebrow">Decision intelligence</p>
        <h2 className="section-title">Core capabilities that power defendable outcomes</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Consensus-backed risk posture</h3>
            <p>Cross-agent synthesis generates confidence-aware recommendations with explicit conflict visibility.</p>
          </article>
          <article className="feature-card">
            <h3>Release governance controls</h3>
            <p>Go/No-Go recommendations include risk level, rationale, and traceable decision context.</p>
          </article>
          <article className="feature-card">
            <h3>Workflow governance runs</h3>
            <p>Cost, security, and post-incident workflows produce auditable outcomes and risk resolution history.</p>
          </article>
          <article className="feature-card">
            <h3>Controlled integration + AI config</h3>
            <p>Tenant-scoped connector/provider setup, validation checks, and runtime telemetry posture.</p>
          </article>
        </div>
      </section>

      <section className="section subpage-band subpage-band-dark">
        <p className="section-eyebrow">Operational intelligence</p>
        <h2 className="section-title">From telemetry to defendable governance outcomes</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Correlated incident intelligence</h3>
            <p>Unify severity, confidence, consensus, and recommendation posture in a single operational view.</p>
          </article>
          <article className="feature-card">
            <h3>Release readiness signals</h3>
            <p>Risk posture, rationale, and confidence signals are structured for leadership approvals.</p>
          </article>
          <article className="feature-card">
            <h3>Workflow outcome traceability</h3>
            <p>Each run stores decision, score, payload, and timestamp for repeatable governance review cycles.</p>
          </article>
          <article className="feature-card">
            <h3>Executive summary assurance</h3>
            <p>Leadership-ready narratives and explainability scoring bridge technical outputs and board-level reviews.</p>
          </article>
        </div>
      </section>

      <section className="section subpage-band">
        <p className="section-eyebrow">Governance operations</p>
        <h2 className="section-title">Capability depth across the full decision lifecycle</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Run lifecycle management</h3>
            <p>Queued, running, succeeded, failed, and retried states remain visible and auditable end-to-end.</p>
          </article>
          <article className="feature-card">
            <h3>Case and decision governance</h3>
            <p>Create cases, issue recommendations, approve final actions, and preserve ownership accountability.</p>
          </article>
          <article className="feature-card">
            <h3>Evidence and alert handling</h3>
            <p>Connector payload snapshots and alert acknowledgements are retained for governance follow-through.</p>
          </article>
          <article className="feature-card">
            <h3>Export and reporting assurance</h3>
            <p>Comprehensive report center plus CSV/JSON export continuity for audits and leadership reporting.</p>
          </article>
        </div>
      </section>

      <section className="subpage-cta">
        <div className="subpage-cta-inner">
          <div className="subpage-cta-copy">
            <strong>Validate which capabilities map to your release governance model.</strong>
            <span>See operational flow detail or begin enterprise onboarding directly.</span>
          </div>
          <div className="subpage-cta-actions">
            <Link to="/how-it-works" className="btn btn-ghost">How it works</Link>
            <Link to="/request-access" className="btn btn-primary">Request access</Link>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
