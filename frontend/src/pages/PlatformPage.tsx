import { useEffect, useState } from "react";
import { fetchSignupStatus } from "../api";
import { MarketingLayout } from "./MarketingLayout";
import "../App.css";

export function PlatformPage() {
  const [signupOpen, setSignupOpen] = useState<boolean | null>(null);
  useEffect(() => {
    fetchSignupStatus()
      .then((s) => setSignupOpen(s.tenant_signup_enabled))
      .catch(() => setSignupOpen(false));
  }, []);

  return (
    <MarketingLayout signupOpen={signupOpen}>
      <section className="section">
        <p className="section-eyebrow">Platform</p>
        <h1 className="section-title">Single control plane for governed operational intelligence</h1>
        <p className="section-lead">
          Casantris unifies governance runs, incidents, workflows, and executive summaries in one tenant-aware operational
          platform.
        </p>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Governance Runs</h3>
            <p>Run, queue, retry, and audit operational decisions with evidence-linked outputs.</p>
          </article>
          <article className="feature-card">
            <h3>Incident Intelligence</h3>
            <p>Correlated incidents with consensus/confidence and conflict detection across domains.</p>
          </article>
          <article className="feature-card">
            <h3>Executive Reporting</h3>
            <p>Executive summaries, explainability index, and JSON/CSV exports for audits and leadership reviews.</p>
          </article>
          <article className="feature-card">
            <h3>Workflow Orchestration</h3>
            <p>Run release governance, cost spike, security governance, and post-incident workflows with decision tracking.</p>
          </article>
          <article className="feature-card">
            <h3>Observability Signals</h3>
            <p>Track request rate, latency, error rate, queue depth, retry behavior, and endpoint pressure in one dashboard.</p>
          </article>
          <article className="feature-card">
            <h3>Tenant Control</h3>
            <p>Superadmin and tenant-admin boundaries keep multi-organization governance isolated and manageable.</p>
          </article>
        </div>
      </section>

      <section className="section section-alt">
        <p className="section-eyebrow">Architecture</p>
        <h2 className="section-title">Designed for accountable operations at scale</h2>
        <p className="section-lead">
          The platform combines API-driven governance workflows, background run processing, connector telemetry, and
          operational observability into a deployable enterprise stack.
        </p>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Governance API Layer</h3>
            <p>Dedicated endpoints for runs, cases, decisions, incidents, workflows, exports, and policy controls.</p>
          </article>
          <article className="feature-card">
            <h3>Background Processing</h3>
            <p>Asynchronous run queue with retries, lifecycle audits, and evidence capture for traceability.</p>
          </article>
          <article className="feature-card">
            <h3>Security-Ready Config</h3>
            <p>Tenant-scoped connector/provider settings with validation and encrypted secret storage for sensitive fields.</p>
          </article>
        </div>
      </section>

      <section className="section">
        <p className="section-eyebrow">Business Value</p>
        <h2 className="section-title">What leadership teams get from day one</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Faster Decision Cycles</h3>
            <p>Move from signal overload to governed recommendations with confidence and conflict indicators.</p>
          </article>
          <article className="feature-card">
            <h3>Lower Operational Ambiguity</h3>
            <p>RAR iteration and cross-agent synthesis help reduce uncertainty before high-impact releases.</p>
          </article>
          <article className="feature-card">
            <h3>Audit and Compliance Readiness</h3>
            <p>Exportable reports and event trails support internal reviews, audits, and stakeholder communication.</p>
          </article>
        </div>
      </section>
    </MarketingLayout>
  );
}
