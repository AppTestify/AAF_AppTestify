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
            <p className="hero-kicker">Enterprise governance platform</p>
            <h1 className="hero-title">Governed delivery intelligence for DevOps, SRE, FinOps, and security</h1>
            <p className="hero-lead">
              Casantris gives leadership and operators one workspace for run governance, incident correlation, release
              decisions, and executive-ready summaries with traceable evidence.
            </p>
            <div className="hero-actions">
              <Link to="/how-it-works" className="btn btn-ghost">
                Move to Ops
              </Link>
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
              <Link to="/platform" className="btn btn-ghost">
                View platform overview
              </Link>
            </div>
            <p className="hero-note">
              {signupOpen === false
                ? "Self-service signup is disabled on this deployment. Sign in with credentials issued by your administrator."
                : signupOpen === null
                  ? "Checking availability…"
                  : "Provision a dedicated tenant and administrator in minutes — SSO-ready architecture for phased enterprise rollout."}
            </p>
          </div>
          <div className="hero-visual" aria-hidden="true">
            <div className="hero-panel">
              <div className="hero-panel-top">
                <span className="hero-panel-dots" />
                <span className="hero-panel-title">Governance run</span>
              </div>
              <div className="hero-panel-metrics">
                <div className="hero-metric">
                  <span className="hero-metric-label">Consensus</span>
                  <span className="hero-metric-value hero-metric-value--good">0.72</span>
                </div>
                <div className="hero-metric">
                  <span className="hero-metric-label">RAR</span>
                  <span className="hero-metric-value">Clear</span>
                </div>
                <div className="hero-metric">
                  <span className="hero-metric-label">XI score</span>
                  <span className="hero-metric-value">0.84</span>
                </div>
              </div>
              <div className="hero-panel-chart">
                <span className="hero-bar hero-bar--a" />
                <span className="hero-bar hero-bar--b" />
                <span className="hero-bar hero-bar--c" />
                <span className="hero-bar hero-bar--d" />
              </div>
              <p className="hero-panel-caption">Illustrative metrics — your pipeline, your thresholds.</p>
            </div>
          </div>
        </div>
      </section>

      <div className="trust-bar">
        <div className="trust-bar-inner">
          <span className="trust-item">
            <strong>Governed operations</strong> with role-based approvals
          </span>
          <span className="trust-sep" aria-hidden="true" />
          <span className="trust-item">
            <strong>Cross-domain visibility</strong> across delivery, reliability, cost, and security
          </span>
          <span className="trust-sep" aria-hidden="true" />
          <span className="trust-item">
            <strong>Executive-ready</strong> incident and release summaries
          </span>
          <span className="trust-sep" aria-hidden="true" />
          <span className="trust-item">
            <strong>Audit-ready</strong> evidence trails and exportable reports
          </span>
        </div>
      </div>

      <section id="platform" className="section section-tight">
        <p className="section-eyebrow">Platform</p>
        <h2 className="section-title">Built for program, engineering, and operations leadership</h2>
        <p className="section-lead">
          Casantris combines tenant-scoped governance runs, case workflows, audits, and observability into a single
          control surface so teams can move from alerts to accountable decisions faster.
        </p>
      </section>

      <section id="product" className="section">
        <div className="feature-grid">
          <article className="feature-card">
            <div className="feature-icon" aria-hidden="true">
              ◇
            </div>
            <h3>Consensus &amp; RAR</h3>
            <p>
              Multi-agent findings are scored into consensus and conflict indicators, with RAR re-analysis available when
              confidence is low.
            </p>
          </article>
          <article className="feature-card">
            <div className="feature-icon" aria-hidden="true">
              ⎘
            </div>
            <h3>Controlled connectors</h3>
            <p>
              Start deterministic in simulation mode, then enable live GitHub/Jira/FinOps paths with tenant-level
              validation and controls.
            </p>
          </article>
          <article className="feature-card">
            <div className="feature-icon" aria-hidden="true">
              ◎
            </div>
            <h3>Executive-ready narrative</h3>
            <p>
              Correlated incidents, release-governance recommendations, and executive summaries are rendered for
              technical and non-technical stakeholders.
            </p>
          </article>
        </div>
      </section>

      <section id="how" className="section section-alt">
        <div className="split-section">
          <div>
            <p className="section-eyebrow">Workflow</p>
            <h2 className="section-title">How it works</h2>
            <ol className="steps steps--enterprise">
              <li>
                <span className="step-num">1</span>
                <div>
                  <strong>Ingest evidence</strong>
                  <p>Connect delivery signals from toolchain sources you approve — simulated or production.</p>
                </div>
              </li>
              <li>
                <span className="step-num">2</span>
                <div>
                  <strong>Run governance</strong>
                  <p>Pose PM-grade questions; agents contribute perspectives and the pipeline reconciles evidence.</p>
                </div>
              </li>
              <li>
                <span className="step-num">3</span>
                <div>
                  <strong>Decide with traceability</strong>
                  <p>Review scores, RAR status, and markdown summaries suitable for audit and exec readouts.</p>
                </div>
              </li>
            </ol>
          </div>
          <div className="integration-card">
            <h3 className="integration-title">Current integration maturity</h3>
            <ul className="integration-list">
              <li>Live-capable: GitHub, Jira, FinOps file inputs</li>
              <li>Simulation-ready: Azure, AWS, policy and telemetry signals</li>
              <li>Tenant-scoped connector and provider validation</li>
              <li>JSON/CSV exports for runs and audit events</li>
            </ul>
            <p className="integration-note">Connector mode is deployment-configurable so teams can safely move from pilot to production.</p>
          </div>
        </div>
      </section>

      <section id="enterprise" className="section">
        <div className="enterprise-band">
          <div>
            <p className="section-eyebrow section-eyebrow--on-dark">Enterprise</p>
            <h2 className="enterprise-title">Operate with the rigor your governance model demands</h2>
            <p className="enterprise-lead">
              Use superadmin and tenant-admin separation, auditable event trails, and lead-to-tenant onboarding workflows
              to scale governed operations across organizations.
            </p>
          </div>
          <ul className="enterprise-bullets">
            <li>Tenant isolation with role-based access and approval workflows</li>
            <li>Release governance, cost-spike, and security review workflow runs</li>
            <li>Dashboard visibility across incidents, telemetry, and workflow outcomes</li>
          </ul>
        </div>
      </section>
    </MarketingLayout>
  );
}
