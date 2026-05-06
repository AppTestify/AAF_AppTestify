import { useEffect, useState } from "react";
import { fetchSignupStatus } from "../api";
import { MarketingLayout } from "./MarketingLayout";
import "../App.css";

export function EnterprisePage() {
  const [signupOpen, setSignupOpen] = useState<boolean | null>(null);
  useEffect(() => {
    fetchSignupStatus()
      .then((s) => setSignupOpen(s.tenant_signup_enabled))
      .catch(() => setSignupOpen(false));
  }, []);

  return (
    <MarketingLayout signupOpen={signupOpen}>
      <section className="section">
        <p className="section-eyebrow">Enterprise</p>
        <h1 className="section-title">Enterprise controls, trust posture, and governance continuity</h1>
        <div className="enterprise-band" style={{ marginTop: "1rem" }}>
          <div>
            <p className="section-eyebrow section-eyebrow--on-dark">Controls</p>
            <h2 className="enterprise-title">Built for multi-organization governance at scale</h2>
            <p className="enterprise-lead">
              Superadmin boundaries, tenant-admin operations, request-access onboarding, and audit-ready workflows deliver a
              defensible enterprise operating model.
            </p>
          </div>
          <ul className="enterprise-bullets">
            <li>Superadmin tenant control and lead-to-tenant conversion workflow</li>
            <li>Tenant-scoped settings, connectors, providers, and policy boundaries</li>
            <li>Auditable runs, decisions, acknowledgements, and export continuity</li>
            <li>Role-aware controls for superadmin, tenant admin, and reviewers</li>
          </ul>
        </div>
      </section>

      <section className="section section-alt">
        <p className="section-eyebrow">Security & Governance</p>
        <h2 className="section-title">Controls that support enterprise assurance models</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Tenant isolation</h3>
            <p>Configuration, governance outputs, and workflow records remain tenant-scoped for strict operational boundaries.</p>
          </article>
          <article className="feature-card">
            <h3>Session and role controls</h3>
            <p>JWT session model with role-constrained access keeps platform and tenant operations separated.</p>
          </article>
          <article className="feature-card">
            <h3>Audit-first actions</h3>
            <p>Run events, approvals, acknowledgements, and status transitions remain preserved for accountability.</p>
          </article>
          <article className="feature-card">
            <h3>Explainable decisioning</h3>
            <p>Executive summaries, confidence values, and rationale outputs keep decisions reviewable by business and technical teams.</p>
          </article>
        </div>
      </section>

      <section className="section">
        <p className="section-eyebrow">Rollout Model</p>
        <h2 className="section-title">How enterprises roll out Casantris across teams</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Phase 1: Controlled pilot</h3>
            <p>Start with one tenant, baseline telemetry, and governance runs to establish decision standards.</p>
          </article>
          <article className="feature-card">
            <h3>Phase 2: Cross-team expansion</h3>
            <p>Onboard additional org units with tenant templates and shared governance reporting conventions.</p>
          </article>
          <article className="feature-card">
            <h3>Phase 3: Executive governance</h3>
            <p>Use workflow outcomes and executive summaries to standardize portfolio-level release governance.</p>
          </article>
          <article className="feature-card">
            <h3>Phase 4: Continuous optimization</h3>
            <p>Iterate on policies, confidence triggers, and connector coverage to reduce operational risk over time.</p>
          </article>
        </div>
      </section>
    </MarketingLayout>
  );
}
