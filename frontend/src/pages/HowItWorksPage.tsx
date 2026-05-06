import { useEffect, useState } from "react";
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
      <section className="section section-alt">
        <p className="section-eyebrow">How It Works</p>
        <h1 className="section-title">From signals to governed decisions</h1>
        <ol className="steps steps--enterprise" style={{ marginTop: "1rem" }}>
          <li>
            <span className="step-num">1</span>
            <div>
              <strong>Configure tenant and integrations</strong>
              <p>Set connector and provider configuration with explicit validation checks.</p>
            </div>
          </li>
          <li>
            <span className="step-num">2</span>
            <div>
              <strong>Run governance analysis</strong>
              <p>Generate findings, correlated incidents, consensus scores, and explainable summaries.</p>
            </div>
          </li>
          <li>
            <span className="step-num">3</span>
            <div>
              <strong>Operate workflows</strong>
              <p>Execute release/cost/security/post-incident workflows with auditable outcomes.</p>
            </div>
          </li>
          <li>
            <span className="step-num">4</span>
            <div>
              <strong>Export and govern</strong>
              <p>Use reports, audit events, and dashboard telemetry to drive accountable operations.</p>
            </div>
          </li>
        </ol>
      </section>

      <section className="section">
        <p className="section-eyebrow">Workflow Breakdown</p>
        <h2 className="section-title">Detailed execution path in production teams</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Step A: Tenant Readiness</h3>
            <p>Define tenant defaults, governance policy thresholds, connector posture, and AI provider strategy.</p>
          </article>
          <article className="feature-card">
            <h3>Step B: Evidence Ingestion</h3>
            <p>Collect connector signals and run-level evidence snapshots that become the factual base for decisions.</p>
          </article>
          <article className="feature-card">
            <h3>Step C: Intelligence Synthesis</h3>
            <p>Agent findings are synthesized into incidents with consensus, confidence, conflict flags, and recommendations.</p>
          </article>
          <article className="feature-card">
            <h3>Step D: Governance Action</h3>
            <p>Teams execute release/cost/security workflows and apply approvals or mitigations with full traceability.</p>
          </article>
        </div>
      </section>

      <section className="section section-alt">
        <p className="section-eyebrow">Operational Cadence</p>
        <h2 className="section-title">How teams typically run Casantris weekly</h2>
        <ol className="steps steps--enterprise" style={{ marginTop: "1rem" }}>
          <li>
            <span className="step-num">1</span>
            <div>
              <strong>Daily monitoring</strong>
              <p>Track dashboard KPIs, incident changes, and workflow outcomes in near real-time.</p>
            </div>
          </li>
          <li>
            <span className="step-num">2</span>
            <div>
              <strong>Pre-release governance</strong>
              <p>Run release posture checks, inspect high-risk incidents, and decide go/no-go with clear rationale.</p>
            </div>
          </li>
          <li>
            <span className="step-num">3</span>
            <div>
              <strong>Post-incident review</strong>
              <p>Launch post-incident workflow to capture summaries, confidence adjustments, and operational learning.</p>
            </div>
          </li>
          <li>
            <span className="step-num">4</span>
            <div>
              <strong>Reporting and audit prep</strong>
              <p>Export run and audit reports for leadership review, compliance evidence, and monthly governance reporting.</p>
            </div>
          </li>
        </ol>
      </section>
    </MarketingLayout>
  );
}
