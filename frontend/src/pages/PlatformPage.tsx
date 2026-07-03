import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSignupStatus } from "../api";
import { AGENTS, INTEGRATIONS, PIPELINE_STEPS } from "../marketing/content";
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
      <section className="marketing-subhero">
        <div className="marketing-subhero-inner">
          <p className="section-eyebrow">Platform</p>
          <h1 className="section-title">Tool layer → agents → pipeline → workspace</h1>
          <p className="section-lead">
            Casantris is a FastAPI + React governance platform: connectors fetch evidence, seventeen tools produce
            normalized signals, four agents score in parallel, and the orchestrator delivers consensus, utility, and
            explainability to your PM UI.
          </p>
        </div>
      </section>

      <section className="section subpage-band">
        <p className="section-eyebrow">Architecture</p>
        <h2 className="section-title">Three layers, one decision</h2>
        <div className="arch-layers" style={{ marginTop: "1rem" }}>
          <article className="arch-layer-card">
            <span className="arch-layer-label">Layer 1</span>
            <h3>Tool layer</h3>
            <p>Async tools across GitHub, GitLab, Jira Agile, AWS (boto3), and security APIs. Sim fixtures for demos.</p>
          </article>
          <article className="arch-layer-card">
            <span className="arch-layer-label">Layer 2</span>
            <h3>Reasoning core</h3>
            <p>BaseAgent dispatches tools, ConfidenceScorer applies weights + staleness, FinOps reasoning core produces Ci.</p>
          </article>
          <article className="arch-layer-card">
            <span className="arch-layer-label">Layer 3</span>
            <h3>Agent output</h3>
            <p>Structured AgentOpinion: claim, confidence, evidence[], raw_signals — consumed by consensus and utility.</p>
          </article>
        </div>
      </section>

      <section className="section subpage-band subpage-band-dark">
        <p className="section-eyebrow">Orchestration</p>
        <h2 className="section-title">What happens after agents run</h2>
        <div className="feature-grid" style={{ marginTop: "1rem" }}>
          <article className="feature-card">
            <h3>Consensus</h3>
            <p>Weighted dominant risk theme across DevOps, PM, FinOps, and DevSecOps opinions with conflict penalty.</p>
          </article>
          <article className="feature-card">
            <h3>RAR (Re-Grounded Agentic Reasoning)</h3>
            <p>Re-run agents when consensus is below τ — refresh stale tools or enrich evidence up to max loops.</p>
          </article>
          <article className="feature-card">
            <h3>Utility scoring</h3>
            <p>Global U and per-action affinity (rollback, mitigate, scale, patch/block, observe) from P, Ci, R indices.</p>
          </article>
          <article className="feature-card">
            <h3>Explainability (XI)</h3>
            <p>Checklist-based XI score plus optional LLM executive markdown for the PM view.</p>
          </article>
          <article className="feature-card">
            <h3>Intelligence path</h3>
            <p>Async runs persist agent findings, correlated incidents, and executive summaries to the dashboard.</p>
          </article>
          <article className="feature-card">
            <h3>Dual-path unification</h3>
            <p>Pipeline and intelligence views share consensus logic and PMAgent delivery signals (replacing legacy SRE).</p>
          </article>
        </div>
      </section>

      <section className="section subpage-band">
        <p className="section-eyebrow">Agents</p>
        <h2 className="section-title">Four domain agents, no siloed SRE agent</h2>
        <div className="agent-showcase-grid" style={{ marginTop: "1rem" }}>
          {AGENTS.map((a) => (
            <article key={a.id} className="agent-showcase-card">
              <h3>{a.name}</h3>
              <p>{a.tagline}</p>
              <ul className="agent-tool-list">
                {a.tools.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="section subpage-band subpage-band-dark">
        <p className="section-eyebrow">Connectors</p>
        <h2 className="section-title">Tenant-scoped integration surface</h2>
        <div className="integration-pill-grid" style={{ marginTop: "1rem" }}>
          {INTEGRATIONS.map((item) => (
            <article key={item.name} className="integration-pill-card">
              <h3>{item.name}</h3>
              <p>{item.detail}</p>
            </article>
          ))}
        </div>
        <p className="section-lead" style={{ marginTop: "1.25rem" }}>
          Connectors validate on save, credentials are Fernet-encrypted, and telemetry freshness is tracked per tenant.
        </p>
      </section>

      <section className="section subpage-band">
        <p className="section-eyebrow">Execution sequence</p>
        <h2 className="section-title">From prompt to PM view</h2>
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

      <section className="subpage-cta">
        <div className="subpage-cta-inner">
          <div className="subpage-cta-copy">
            <strong>See the platform in your workspace.</strong>
            <span>Run a governance prompt in sim mode — no credentials required.</span>
          </div>
          <div className="subpage-cta-actions">
            <Link to="/login" className="btn btn-primary">
              Sign in
            </Link>
            <Link to="/capabilities" className="btn btn-ghost">
              All capabilities
            </Link>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
