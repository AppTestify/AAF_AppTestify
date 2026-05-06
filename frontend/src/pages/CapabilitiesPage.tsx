import { useEffect, useState } from "react";
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
      <section className="section">
        <p className="section-eyebrow">Capabilities</p>
        <h1 className="section-title">Operational capabilities delivered in the current product</h1>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Consensus + RAR</h3>
            <p>Cross-agent consensus scoring with re-grounded re-analysis when confidence drops.</p>
          </article>
          <article className="feature-card">
            <h3>Release Governance</h3>
            <p>Go/No-Go posture with risk-level recommendation and rationale.</p>
          </article>
          <article className="feature-card">
            <h3>Workflow Runs</h3>
            <p>Cost spike, security governance, and post-incident review workflows with tracked outcomes.</p>
          </article>
          <article className="feature-card">
            <h3>Connectors & AI Config</h3>
            <p>Tenant-scoped connector/provider setup, validation, and telemetry status.</p>
          </article>
        </div>
      </section>

      <section className="section section-alt">
        <p className="section-eyebrow">Operational Intelligence</p>
        <h2 className="section-title">From telemetry to explainable governance outcomes</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Correlated Incident Views</h3>
            <p>Unify incident severity, consensus score, confidence, and recommendation in one operational object.</p>
          </article>
          <article className="feature-card">
            <h3>Release Readiness Signals</h3>
            <p>Release governance decisions surface risk level, rationale, and decision posture for leadership approvals.</p>
          </article>
          <article className="feature-card">
            <h3>Workflow Outcome Tracking</h3>
            <p>Each workflow run stores decision, score, output payload, and timestamp for repeatable governance reviews.</p>
          </article>
          <article className="feature-card">
            <h3>Executive Summary Layer</h3>
            <p>Human-readable summaries and XI scoring translate technical outcomes for PM and executive stakeholders.</p>
          </article>
        </div>
      </section>

      <section className="section">
        <p className="section-eyebrow">Governance Operations</p>
        <h2 className="section-title">Capability depth across the full decision lifecycle</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Run Lifecycle Management</h3>
            <p>Queued, running, succeeded, failed, and retried states are visible and auditable throughout processing.</p>
          </article>
          <article className="feature-card">
            <h3>Case and Decision Workbench</h3>
            <p>Create cases, propose decisions, approve final actions, and maintain ownership and status accountability.</p>
          </article>
          <article className="feature-card">
            <h3>Evidence and Alert Handling</h3>
            <p>Connector evidence snapshots and alert acknowledgements are captured for governance and operational follow-through.</p>
          </article>
          <article className="feature-card">
            <h3>Export and Reporting</h3>
            <p>Comprehensive report center plus CSV/JSON exports for governance run summaries and audit event streams.</p>
          </article>
        </div>
      </section>
    </MarketingLayout>
  );
}
