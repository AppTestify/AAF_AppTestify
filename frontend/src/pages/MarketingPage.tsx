import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSignupStatus } from "../api";
import "../App.css";

export function MarketingPage() {
  const [signupOpen, setSignupOpen] = useState<boolean | null>(null);

  useEffect(() => {
    fetchSignupStatus()
      .then((s) => setSignupOpen(s.tenant_signup_enabled))
      .catch(() => setSignupOpen(false));
  }, []);

  return (
    <div className="marketing">
      <header className="site-header">
        <div className="site-header-inner site-nav">
          <Link to="/" className="site-logo">
            <span className="site-logo-mark" aria-hidden="true" />
            <span className="site-logo-text">AgileOps</span>
          </Link>
          <nav className="site-nav-links" aria-label="Primary">
            <a href="#platform">Platform</a>
            <a href="#product">Capabilities</a>
            <a href="#how">How it works</a>
            <a href="#enterprise">Enterprise</a>
          </nav>
          <div className="site-nav-cta">
            {signupOpen ? (
              <Link to="/signup" className="btn btn-ghost btn-sm">
                Create organization
              </Link>
            ) : null}
            <Link to="/login" className="btn btn-primary btn-sm">
              Sign in
            </Link>
          </div>
        </div>
      </header>

      <section className="hero">
        <div className="hero-inner">
          <div className="hero-copy">
            <p className="hero-kicker">Enterprise agentic governance</p>
            <h1 className="hero-title">Delivery decisions with evidence, consensus, and control</h1>
            <p className="hero-lead">
              Unify GitHub, JIRA, and cost signals into one governed PM workspace. Model consensus, risk-at-release loops,
              and explainable recommendations your executives and compliance partners can stand behind.
            </p>
            <div className="hero-actions">
              {signupOpen ? (
                <Link to="/signup" className="btn btn-primary">
                  Start your organization
                </Link>
              ) : (
                <Link to="/login" className="btn btn-primary">
                  Sign in to workspace
                </Link>
              )}
              <a href="#platform" className="btn btn-ghost">
                View platform overview
              </a>
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
            <strong>Multi-tenant</strong> isolated organizations
          </span>
          <span className="trust-sep" aria-hidden="true" />
          <span className="trust-item">
            <strong>JWT</strong> session model
          </span>
          <span className="trust-sep" aria-hidden="true" />
          <span className="trust-item">
            <strong>Explainable</strong> outputs for stakeholders
          </span>
          <span className="trust-sep" aria-hidden="true" />
          <span className="trust-item">
            <strong>Simulation or live</strong> connectors
          </span>
        </div>
      </div>

      <section id="platform" className="section section-tight">
        <p className="section-eyebrow">Platform</p>
        <h2 className="section-title">Built for program and engineering leadership</h2>
        <p className="section-lead">
          AgileOps Agentic Framework orchestrates retrieval, normalization, and scoring so PMs spend less time stitching
          spreadsheets and more time steering releases.
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
              Tune consensus thresholds and risk-at-release loops to match your risk appetite before code reaches
              production.
            </p>
          </article>
          <article className="feature-card">
            <div className="feature-icon" aria-hidden="true">
              ⎘
            </div>
            <h3>Controlled connectors</h3>
            <p>
              Start with deterministic simulation fixtures, then graduate to live GitHub, JIRA, and FinOps-style cost
              inputs on your timeline.
            </p>
          </article>
          <article className="feature-card">
            <div className="feature-icon" aria-hidden="true">
              ◎
            </div>
            <h3>Executive-ready narrative</h3>
            <p>
              Utility scoring and structured explanations translate agent output into briefings your leadership team can
              consume without a PhD in ML.
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
            <h3 className="integration-title">Integrations</h3>
            <ul className="integration-list">
              <li>GitHub</li>
              <li>JIRA Cloud</li>
              <li>FinOps / cost signals</li>
              <li>Custom fixtures</li>
            </ul>
            <p className="integration-note">Connector mode is configurable per deployment; tenant-scoped policies roadmap.</p>
          </div>
        </div>
      </section>

      <section id="enterprise" className="section">
        <div className="enterprise-band">
          <div>
            <p className="section-eyebrow section-eyebrow--on-dark">Enterprise</p>
            <h2 className="enterprise-title">Operate with the rigor your governance model demands</h2>
            <p className="enterprise-lead">
              Role separation between platform superadministrators and tenant administrators, clear audit surfaces on
              evidence and outputs, and a path from pilot tenants to organization-wide rollout.
            </p>
          </div>
          <ul className="enterprise-bullets">
            <li>Tenant isolation with administrator-controlled access</li>
            <li>Structured governance API for automation and integration</li>
            <li>Dark workspace console optimized for daily operator use</li>
          </ul>
        </div>
      </section>

      <footer className="site-footer">
        <div className="site-footer-grid">
          <div className="site-footer-brand">
            <div className="site-footer-name-row">
              <span className="site-logo-mark site-logo-mark--footer" aria-hidden="true" />
              <span className="site-footer-name">AgileOps</span>
            </div>
            <p className="site-footer-tagline">Agentic framework for governed delivery intelligence.</p>
          </div>
          <div className="site-footer-col">
            <span className="site-footer-heading">Product</span>
            <Link to="/login">Workspace</Link>
            {signupOpen ? <Link to="/signup">Create organization</Link> : null}
            <a href="#platform">Platform</a>
          </div>
          <div className="site-footer-col">
            <span className="site-footer-heading">Company</span>
            <a href="#enterprise">Enterprise</a>
            <a href="#how">How it works</a>
          </div>
        </div>
        <div className="site-footer-bottom">
          <span>© {new Date().getFullYear()} AgileOps. All rights reserved.</span>
          <Link to="/login">Sign in</Link>
        </div>
      </footer>
    </div>
  );
}
