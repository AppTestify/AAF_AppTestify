import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSignupStatus } from "../api";
import { INTEGRATIONS, WORKSPACE_FEATURES } from "../marketing/content";
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
      <section className="marketing-subhero">
        <div className="marketing-subhero-inner">
          <p className="section-eyebrow">Enterprise</p>
          <h1 className="section-title">Multi-tenant governance with production-grade controls</h1>
          <p className="section-lead">
            Tenant isolation, encrypted connector secrets, RBAC, audit events, and signed share links — so your release
            governance model scales across organizations without losing traceability.
          </p>
        </div>
      </section>

      <section className="section subpage-band subpage-band-dark">
        <p className="section-eyebrow">Controls</p>
        <h2 className="section-title">Built for regulated and high-velocity teams alike</h2>
        <div className="enterprise-band" style={{ marginTop: "1rem" }}>
          <div>
            <p className="section-eyebrow section-eyebrow--on-dark">Assurance model</p>
            <h2 className="enterprise-title">Every decision links to tool evidence</h2>
            <p className="enterprise-lead">
              Agent opinions ship with human-readable evidence strings and expandable raw_signals — not black-box scores.
              Cases, approvals, and exports preserve the full chain for internal controls and external audits.
            </p>
          </div>
          <ul className="enterprise-bullets">
            <li>Superadmin tenant provisioning and request-access lead conversion</li>
            <li>Tenant-scoped GitHub, GitLab, Jira, AWS, Azure, FinOps connector config with validation</li>
            <li>httpOnly session cookies, refresh tokens, DB-backed rate limiting</li>
            <li>Fernet-encrypted credentials at rest for connector and LLM keys</li>
          </ul>
        </div>
      </section>

      <section className="section subpage-band">
        <p className="section-eyebrow">Integrations at scale</p>
        <h2 className="section-title">Connect the systems your agents already read</h2>
        <div className="integration-pill-grid" style={{ marginTop: "1rem" }}>
          {INTEGRATIONS.map((item) => (
            <article key={item.name} className="integration-pill-card">
              <h3>{item.name}</h3>
              <p>{item.detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section subpage-band subpage-band-dark">
        <p className="section-eyebrow">Security & governance</p>
        <h2 className="section-title">Enterprise assurance features</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Tenant isolation</h3>
            <p>Runs, cases, evidence snapshots, and connector config remain strictly tenant-scoped.</p>
          </article>
          <article className="feature-card">
            <h3>RBAC</h3>
            <p>Superadmin, tenant admin, approver, and reviewer roles with permission-gated API routes.</p>
          </article>
          <article className="feature-card">
            <h3>Audit-first actions</h3>
            <p>Governance audit events capture config changes, decisions, and acknowledgements.</p>
          </article>
          <article className="feature-card">
            <h3>Signed share links</h3>
            <p>JWT-signed run snapshots with optional PDF one-pager for external stakeholder review.</p>
          </article>
          <article className="feature-card">
            <h3>Policy thresholds</h3>
            <p>Tenant governance policies for consensus and XI minimums before release approval.</p>
          </article>
          <article className="feature-card">
            <h3>Observability</h3>
            <p>Prometheus metrics, OTLP tracing hooks, SLO error-budget signals in the decision lifecycle view.</p>
          </article>
        </div>
      </section>

      <section className="section subpage-band">
        <p className="section-eyebrow">Workspace depth</p>
        <h2 className="section-title">What enterprises get in the product</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          {WORKSPACE_FEATURES.map((f) => (
            <article key={f.title} className="feature-card">
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section subpage-band subpage-band-dark">
        <p className="section-eyebrow">Rollout model</p>
        <h2 className="section-title">Four phases to production governance</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Phase 1: Sim pilot</h3>
            <p>Run governance with fixtures — validate agent evidence and PM workflow without live credentials.</p>
          </article>
          <article className="feature-card">
            <h3>Phase 2: Live connectors</h3>
            <p>Wire GitHub, GitLab, Jira board ID, and AWS keys. Enable workflow_run webhooks for CI freshness.</p>
          </article>
          <article className="feature-card">
            <h3>Phase 3: Case governance</h3>
            <p>Formalize go/no-go with cases, approvers, and portfolio-linked release tracking.</p>
          </article>
          <article className="feature-card">
            <h3>Phase 4: Executive reporting</h3>
            <p>Standardize incident intelligence, executive summaries, and CSV exports for leadership forums.</p>
          </article>
        </div>
      </section>

      <section className="subpage-cta">
        <div className="subpage-cta-inner">
          <div className="subpage-cta-copy">
            <strong>Plan your enterprise rollout with the Casantris team.</strong>
            <span>Request access or explore the platform architecture first.</span>
          </div>
          <div className="subpage-cta-actions">
            <Link to="/request-access" className="btn btn-primary">
              Talk to sales
            </Link>
            <Link to="/platform" className="btn btn-ghost">
              Platform architecture
            </Link>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
