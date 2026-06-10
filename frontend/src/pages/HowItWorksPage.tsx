import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSignupStatus } from "../api";
import { PIPELINE_STEPS, AGENTS } from "../marketing/content";
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
          <p className="section-eyebrow">How it works</p>
          <h1 className="section-title">Prompt → tools → agents → consensus → decision</h1>
          <p className="section-lead">
            A deterministic governance pipeline with optional LLM enhancement — built for release reviews, not chat
            experiments.
          </p>
        </div>
      </section>

      <section className="section subpage-band subpage-band-dark">
        <p className="section-eyebrow">End-to-end flow</p>
        <h2 className="section-title">The governance pipeline</h2>
        <ol className="steps steps--enterprise" style={{ marginTop: "1rem" }}>
          {PIPELINE_STEPS.map((s) => (
            <li key={s.step}>
              <span className="step-num">{s.step}</span>
              <div>
                <strong>{s.title}</strong>
                <p>{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="section subpage-band">
        <p className="section-eyebrow">Inside each agent</p>
        <h2 className="section-title">BaseAgent: parallel tools, weighted scoring</h2>
        <div className="pipeline-diagram" style={{ marginTop: "1rem" }}>
          <div className="pipeline-diagram-row">
            <span className="pipeline-diagram-node">EvidencePackage</span>
            <span className="pipeline-diagram-arrow">→</span>
            <span className="pipeline-diagram-node pipeline-diagram-node--accent">BaseAgent</span>
          </div>
          <div className="pipeline-diagram-fan">
            {AGENTS.flatMap((a) => a.tools.slice(0, 2)).map((t) => (
              <span key={t} className="pipeline-diagram-tool">
                {t}
              </span>
            ))}
            <span className="pipeline-diagram-tool pipeline-diagram-tool--more">+9 more tools</span>
          </div>
          <div className="pipeline-diagram-row">
            <span className="pipeline-diagram-node">ConfidenceScorer</span>
            <span className="pipeline-diagram-arrow">→</span>
            <span className="pipeline-diagram-node">claim + evidence[]</span>
          </div>
        </div>
        <div className="feature-grid" style={{ marginTop: "1.25rem" }}>
          <article className="feature-card">
            <h3>Staleness penalties</h3>
            <p>DevOps, PM, DevSecOps: 4h window × 0.5 factor. FinOps: 6h × 0.4 (AWS billing lag).</p>
          </article>
          <article className="feature-card">
            <h3>RAR loop</h3>
            <p>When consensus &lt; τ, stale tools re-fetch via live connector refresh or evidence enrichment.</p>
          </article>
          <article className="feature-card">
            <h3>Webhook freshness</h3>
            <p>GitHub workflow_run webhooks invalidate CI tool cache for near-real-time pass rates.</p>
          </article>
          <article className="feature-card">
            <h3>Sim + live modes</h3>
            <p>CONNECTOR_MODE=sim uses fixtures for demos; live mode calls GitHub, Jira Agile, and AWS APIs.</p>
          </article>
        </div>
      </section>

      <section className="section subpage-band subpage-band-dark">
        <p className="section-eyebrow">Weekly cadence</p>
        <h2 className="section-title">How teams use Casantris in practice</h2>
        <ol className="steps steps--enterprise" style={{ marginTop: "1rem" }}>
          <li>
            <span className="step-num">1</span>
            <div>
              <strong>Configure connectors</strong>
              <p>GitHub repo + PAT, Jira project + board ID, AWS keys for FinOps — validate in Settings.</p>
            </div>
          </li>
          <li>
            <span className="step-num">2</span>
            <div>
              <strong>Run governance before release</strong>
              <p>Ask “Is the release branch safe to merge?” — review agent evidence, Global U, and recommended action.</p>
            </div>
          </li>
          <li>
            <span className="step-num">3</span>
            <div>
              <strong>Open a case if blocked</strong>
              <p>Escalate to case/decision workflow with approvers and preserved audit trail.</p>
            </div>
          </li>
          <li>
            <span className="step-num">4</span>
            <div>
              <strong>Export for leadership</strong>
              <p>Executive summary, incident findings (DevOps + PM + FinOps + DevSecOps), CSV/JSON reports.</p>
            </div>
          </li>
        </ol>
      </section>

      <section className="subpage-cta">
        <div className="subpage-cta-inner">
          <div className="subpage-cta-copy">
            <strong>Ready to run your first governance prompt?</strong>
            <span>Sign in to the workspace or request enterprise onboarding.</span>
          </div>
          <div className="subpage-cta-actions">
            <Link to="/login" className="btn btn-primary">
              Open workspace
            </Link>
            <Link to="/enterprise" className="btn btn-ghost">
              Enterprise rollout
            </Link>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
