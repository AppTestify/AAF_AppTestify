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
        <h1 className="section-title">Enterprise controls, governance, and onboarding</h1>
        <div className="enterprise-band" style={{ marginTop: "1rem" }}>
          <div>
            <p className="section-eyebrow section-eyebrow--on-dark">Controls</p>
            <h2 className="enterprise-title">Built for multi-organization governance at scale</h2>
            <p className="enterprise-lead">
              Superadmin control, tenant-admin operations, request-access leads, and conversion to tenant workflow are all
              available in the current platform.
            </p>
          </div>
          <ul className="enterprise-bullets">
            <li>Superadmin-only tenant management and lead conversion</li>
            <li>Tenant-scoped settings, connectors, providers, and policy controls</li>
            <li>Auditable runs, decisions, acknowledgements, and exportable reports</li>
            <li>Role-based access posture for superadmin, tenant admin, and reviewer workflows</li>
          </ul>
        </div>
      </section>

      <section className="section section-alt">
        <p className="section-eyebrow">Security & Governance</p>
        <h2 className="section-title">Controls that support enterprise operating models</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Tenant Isolation</h3>
            <p>Configuration, governance outputs, and workflow records are tenant-scoped for clean operational boundaries.</p>
          </article>
          <article className="feature-card">
            <h3>Session and Role Controls</h3>
            <p>JWT session model with role-constrained access keeps superadmin and tenant operations clearly separated.</p>
          </article>
          <article className="feature-card">
            <h3>Audit-First Actions</h3>
            <p>Run events, approvals, acknowledgements, and status transitions are preserved for transparent accountability.</p>
          </article>
          <article className="feature-card">
            <h3>Explainable Decisioning</h3>
            <p>Executive summaries, confidence values, and rationale outputs make decisions reviewable by technical and business teams.</p>
          </article>
        </div>
      </section>

      <section className="section">
        <p className="section-eyebrow">Rollout Model</p>
        <h2 className="section-title">How enterprises deploy Casantris across teams</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Phase 1: Controlled Pilot</h3>
            <p>Start with one tenant, baseline telemetry, and governance runs to establish decision standards.</p>
          </article>
          <article className="feature-card">
            <h3>Phase 2: Cross-Team Expansion</h3>
            <p>Onboard additional org units with tenant templates and shared governance reporting conventions.</p>
          </article>
          <article className="feature-card">
            <h3>Phase 3: Executive Governance</h3>
            <p>Use workflow outcomes and executive summaries to standardize portfolio-level release governance.</p>
          </article>
          <article className="feature-card">
            <h3>Phase 4: Continuous Optimization</h3>
            <p>Iterate on policies, RAR triggers, and connector coverage to improve confidence and reduce operational risk.</p>
          </article>
        </div>
      </section>
    </MarketingLayout>
  );
}
