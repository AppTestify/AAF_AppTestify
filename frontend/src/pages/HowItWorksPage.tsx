import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSignupStatus } from "../api";
import { MarketingLayout } from "./MarketingLayout";
import "../App.css";

export function HowItWorksPage() {
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
          <p className="section-eyebrow">How It Works</p>
          <h1 className="section-title">From operational signals to auditable governance decisions</h1>
          <p className="section-lead">A structured execution rhythm that keeps controls, context, and outcomes aligned.</p>
        </div>
      </section>

      <section className="section subpage-band subpage-band-dark">
        <p className="section-eyebrow">Execution model</p>
        <h2 className="section-title">A repeatable trust-first operating sequence</h2>
        <ol className="steps steps--enterprise" style={{ marginTop: "1rem" }}>
          <li>
            <span className="step-num">1</span>
            <div>
              <strong>Establish governance boundaries</strong>
              <p>Configure tenant scope, access roles, and controlled integration posture before execution.</p>
            </div>
          </li>
          <li>
            <span className="step-num">2</span>
            <div>
              <strong>Run risk intelligence workflows</strong>
              <p>Generate findings, correlated incidents, confidence posture, and explainable recommendations.</p>
            </div>
          </li>
          <li>
            <span className="step-num">3</span>
            <div>
              <strong>Execute controlled decisions</strong>
              <p>Apply release/cost/security/post-incident workflows with approval traceability.</p>
            </div>
          </li>
          <li>
            <span className="step-num">4</span>
            <div>
              <strong>Report and assure</strong>
              <p>Use exports, audit streams, and telemetry posture to support compliance and leadership assurance.</p>
            </div>
          </li>
        </ol>
      </section>

      <section className="section subpage-band">
        <p className="section-eyebrow">Workflow Breakdown</p>
        <h2 className="section-title">Detailed execution model for production teams</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Step A: Tenant readiness</h3>
            <p>Define defaults, policy thresholds, connector boundaries, and AI provider posture.</p>
          </article>
          <article className="feature-card">
            <h3>Step B: Evidence ingestion</h3>
            <p>Collect connector signals and evidence snapshots as the factual base for governance recommendations.</p>
          </article>
          <article className="feature-card">
            <h3>Step C: Intelligence synthesis</h3>
            <p>Findings are synthesized into incidents with consensus, confidence, conflict flags, and recommended actions.</p>
          </article>
          <article className="feature-card">
            <h3>Step D: Governance action</h3>
            <p>Teams execute workflow actions and apply approvals or mitigations with full traceability.</p>
          </article>
        </div>
      </section>

      <section className="section subpage-band subpage-band-dark">
        <p className="section-eyebrow">Operational Cadence</p>
        <h2 className="section-title">How trusted operating teams run Casantris weekly</h2>
        <ol className="steps steps--enterprise" style={{ marginTop: "1rem" }}>
          <li>
            <span className="step-num">1</span>
            <div>
              <strong>Daily control monitoring</strong>
              <p>Track dashboard KPIs, incident movement, and workflow posture in near real-time.</p>
            </div>
          </li>
          <li>
            <span className="step-num">2</span>
            <div>
              <strong>Pre-release governance review</strong>
              <p>Run release posture checks, inspect high-risk incidents, and execute go/no-go with rationale.</p>
            </div>
          </li>
          <li>
            <span className="step-num">3</span>
            <div>
              <strong>Post-incident assurance</strong>
              <p>Run post-incident workflow to capture summary posture, confidence shifts, and corrective actions.</p>
            </div>
          </li>
          <li>
            <span className="step-num">4</span>
            <div>
              <strong>Reporting and audit readiness</strong>
              <p>Export run and audit reports for leadership review, compliance continuity, and governance forums.</p>
            </div>
          </li>
        </ol>
      </section>

      <section className="subpage-cta">
        <div className="subpage-cta-inner">
          <div className="subpage-cta-copy">
            <strong>Ready to operationalize this cadence with your team?</strong>
            <span>Move from process understanding to enterprise rollout planning.</span>
          </div>
          <div className="subpage-cta-actions">
            <Link to="/enterprise" className="btn btn-ghost">Enterprise rollout</Link>
            <Link to="/request-access" className="btn btn-primary">Request access</Link>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
