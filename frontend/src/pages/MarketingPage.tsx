import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSignupStatus } from "../api";
import { MarketingLayout } from "./MarketingLayout";
import "../App.css";

export function MarketingPage() {
  const [signupOpen, setSignupOpen] = useState<boolean | null>(null);

  useEffect(() => {
    fetchSignupStatus()
      .then((s) => setSignupOpen(s.tenant_signup_enabled))
      .catch(() => setSignupOpen(false));
  }, []);

  return (
    <MarketingLayout signupOpen={signupOpen}>
      <section className="hero">
        <div className="hero-inner">
          <div className="hero-copy">
            <p className="hero-kicker">Enterprise trust platform</p>
            <h1 className="hero-title">The governance layer leadership can defend in every release review</h1>
            <p className="hero-lead">
              Casantris unifies operational evidence, release posture, and accountability controls so leadership teams can
              make high-impact decisions with confidence, traceability, and audit readiness.
            </p>
            <div className="hero-actions">
              <Link to="/enterprise" className="btn btn-ghost">Why enterprises trust Casantris</Link>
              <Link to="/request-access" className="btn btn-ghost">
                Request access
              </Link>
              {signupOpen ? (
                <Link to="/signup" className="btn btn-primary">
                  Start your organization
                </Link>
              ) : (
                <Link to="/login" className="btn btn-primary">
                  Sign in to workspace
                </Link>
              )}
              <Link to="/platform" className="btn btn-ghost">View trust architecture</Link>
            </div>
            <p className="hero-note">
              {signupOpen === false
                ? "Self-service signup is disabled on this deployment. Sign in with credentials issued by your administrator."
                : signupOpen === null
                  ? "Checking availability…"
                  : "Provision a dedicated tenant and administrator in minutes with governance-first controls and enterprise rollout support."}
            </p>
          </div>
          <div className="hero-visual" aria-hidden="true">
            <div className="hero-panel">
              <div className="hero-panel-top">
                <span className="hero-panel-dots" />
                <span className="hero-panel-title">Trust posture snapshot</span>
              </div>
              <div className="hero-panel-metrics">
                <div className="hero-metric">
                  <span className="hero-metric-label">Release risk</span>
                  <span className="hero-metric-value hero-metric-value--good">Low</span>
                </div>
                <div className="hero-metric">
                  <span className="hero-metric-label">Control status</span>
                  <span className="hero-metric-value">Compliant</span>
                </div>
                <div className="hero-metric">
                  <span className="hero-metric-label">Audit trail</span>
                  <span className="hero-metric-value">Complete</span>
                </div>
              </div>
              <div className="hero-panel-chart">
                <span className="hero-bar hero-bar--a" />
                <span className="hero-bar hero-bar--b" />
                <span className="hero-bar hero-bar--c" />
                <span className="hero-bar hero-bar--d" />
              </div>
              <p className="hero-panel-caption">Illustrative trust posture aligned to enterprise governance standards.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="tech-strip" aria-label="Technology stack">
        <div className="tech-strip-inner">
          {["AWS", "Azure", "Google Cloud", "OpenAI", "LangChain", "Docker", "Kubernetes", "PostgreSQL", "React", "Node.js", "Python", "Terraform"].map((tech) => (
            <span key={tech} className="tech-chip">
              {tech}
            </span>
          ))}
        </div>
      </section>

      <div className="trust-bar">
        <div className="trust-bar-inner">
          <span className="trust-item">
            <strong>Defensible release decisions</strong> with explainable evidence
          </span>
          <span className="trust-sep" aria-hidden="true" />
          <span className="trust-item">
            <strong>Control-plane clarity</strong> across delivery, reliability, cost, and security
          </span>
          <span className="trust-sep" aria-hidden="true" />
          <span className="trust-item">
            <strong>Leadership-ready narratives</strong> with operational proof
          </span>
          <span className="trust-sep" aria-hidden="true" />
          <span className="trust-item">
            <strong>Audit continuity</strong> with exportable trails and approvals
          </span>
        </div>
      </div>

      <section id="platform" className="section section-tight">
        <p className="section-eyebrow">Platform</p>
        <h2 className="section-title">Purpose-built for governance accountability</h2>
        <p className="section-lead">
          Casantris combines tenant-scoped workflows, policy-aware review paths, and audit-ready outputs in a single trust
          architecture so teams can move from uncertainty to accountable action quickly.
        </p>
      </section>

      <section id="product" className="section">
        <div className="feature-grid">
          <article className="feature-card">
            <div className="feature-icon" aria-hidden="true">
              ◇
            </div>
            <h3>Evidence-backed decisioning</h3>
            <p>
              Every recommendation links to source evidence and can be challenged, reviewed, and exported with full context.
            </p>
          </article>
          <article className="feature-card">
            <div className="feature-icon" aria-hidden="true">
              ⎘
            </div>
            <h3>Controlled integration posture</h3>
            <p>
              Connector enablement and validation are tenant-scoped, giving platform owners policy-grade control over live
              signal ingress.
            </p>
          </article>
          <article className="feature-card">
            <div className="feature-icon" aria-hidden="true">
              ◎
            </div>
            <h3>Executive trust reporting</h3>
            <p>
              Incident posture, release recommendations, and summary narratives are aligned to leadership governance
              discussions.
            </p>
          </article>
        </div>
      </section>

      <section id="how" className="section section-alt">
        <div className="split-section">
          <div>
            <p className="section-eyebrow">Workflow</p>
            <h2 className="section-title">A trust-first operating model</h2>
            <ol className="steps steps--enterprise">
              <li>
                <span className="step-num">1</span>
                <div>
                  <strong>Establish controlled evidence flow</strong>
                  <p>Enable only approved integrations and validate signal quality before governance workflows consume it.</p>
                </div>
              </li>
              <li>
                <span className="step-num">2</span>
                <div>
                  <strong>Evaluate operational risk</strong>
                  <p>Run governance analysis to produce defensible risk, confidence, and recommendation posture.</p>
                </div>
              </li>
              <li>
                <span className="step-num">3</span>
                <div>
                  <strong>Approve with audit traceability</strong>
                  <p>Capture approvals, outcomes, and supporting rationale for internal controls and external audits.</p>
                </div>
              </li>
            </ol>
          </div>
          <div className="integration-card">
            <h3 className="integration-title">Trust posture coverage</h3>
            <ul className="integration-list">
              <li>Tenant isolation and scoped controls by design</li>
              <li>Role-aware review and decision governance workflow</li>
              <li>Operational telemetry and alert-rule visibility</li>
              <li>JSON/CSV export continuity for assurance reporting</li>
            </ul>
            <p className="integration-note">Deployment mode can transition from controlled pilot to live production with governance controls intact.</p>
          </div>
        </div>
      </section>

      <section id="enterprise" className="section">
        <div className="enterprise-band">
          <div>
            <p className="section-eyebrow section-eyebrow--on-dark">Enterprise</p>
            <h2 className="enterprise-title">Operate with policy-grade rigor and investor-level confidence</h2>
            <p className="enterprise-lead">
              Superadmin boundaries, auditable decision paths, and structured onboarding workflows help organizations scale
              governance without sacrificing speed.
            </p>
          </div>
          <ul className="enterprise-bullets">
            <li>Defensible release posture with traceable rationale</li>
            <li>Governance workflows for cost, security, and reliability scenarios</li>
            <li>Leadership-level visibility into controls, incidents, and outcomes</li>
          </ul>
        </div>
      </section>
    </MarketingLayout>
  );
}
