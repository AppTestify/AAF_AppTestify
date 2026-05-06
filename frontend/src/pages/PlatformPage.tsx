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
        <h1 className="section-title">A trust architecture for enterprise operational governance</h1>
        <p className="section-lead">
          Casantris brings policy controls, evidence continuity, and decision accountability into one tenant-aware control
          plane for engineering and risk leadership.
        </p>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Defensible decision runs</h3>
            <p>Queue, execute, and review governance runs with traceable evidence and repeatable review posture.</p>
          </article>
          <article className="feature-card">
            <h3>Cross-domain incident intelligence</h3>
            <p>Correlate risk signals across reliability, delivery, security, and cost with confidence context.</p>
          </article>
          <article className="feature-card">
            <h3>Leadership assurance reporting</h3>
            <p>Executive narratives and structured exports support review boards, audits, and governance councils.</p>
          </article>
          <article className="feature-card">
            <h3>Policy-backed workflow orchestration</h3>
            <p>Run release, cost, security, and post-incident workflows with formalized decisions and outcomes.</p>
          </article>
          <article className="feature-card">
            <h3>Operational trust telemetry</h3>
            <p>Track burn-rate posture, queue pressure, endpoint risk, and alert-state behavior in one surface.</p>
          </article>
          <article className="feature-card">
            <h3>Enterprise tenant governance</h3>
            <p>Superadmin and tenant-admin boundaries maintain governance isolation across organizations.</p>
          </article>
        </div>
      </section>

      <section className="section section-alt">
        <p className="section-eyebrow">Architecture</p>
        <h2 className="section-title">Designed for accountability at scale</h2>
        <p className="section-lead">
          The platform combines API-governed workflows, background execution controls, connector validation, and
          observability telemetry into a production-ready enterprise stack.
        </p>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Governance API contracts</h3>
            <p>Dedicated contracts for runs, decisions, incidents, workflows, and assurance exports.</p>
          </article>
          <article className="feature-card">
            <h3>Controlled async execution</h3>
            <p>Run queues with retries, lifecycle observability, and durable evidence capture for traceability.</p>
          </article>
          <article className="feature-card">
            <h3>Policy-aware configuration layer</h3>
            <p>Tenant-scoped connector/provider controls with validation and encrypted secret handling for key material.</p>
          </article>
        </div>
      </section>

      <section className="section">
        <p className="section-eyebrow">Business Value</p>
        <h2 className="section-title">Leadership outcomes from day one</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Faster decision confidence</h3>
            <p>Move from fragmented signals to governed recommendations with confidence and conflict indicators.</p>
          </article>
          <article className="feature-card">
            <h3>Reduced release ambiguity</h3>
            <p>Cross-agent synthesis and confidence workflows reduce uncertainty before high-impact releases.</p>
          </article>
          <article className="feature-card">
            <h3>Audit continuity</h3>
            <p>Exportable reports and event trails support internal controls, external audits, and board communication.</p>
          </article>
        </div>
      </section>
    </MarketingLayout>
  );
}
