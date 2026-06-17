import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSignupStatus } from "../api";
import { AGENTS, INTEGRATIONS, PIPELINE_STEPS, TECH_STACK } from "../marketing/content";
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
            <p className="hero-kicker">Multi-agent governance platform</p>
            <h1 className="hero-title">
              Four agents. Seventeen tools. One defensible release decision.
            </h1>
            <p className="hero-lead">
              Casantris runs DevOps, PM, FinOps, and DevSecOps agents in parallel — each calling live GitHub, GitLab, Jira, and AWS
              tools — then scores consensus, utility (U = 0.4·P + 0.3·Ci + 0.3·R), and explainability for leadership-ready
              go/no-go calls.
            </p>
            <div className="hero-actions">
              <Link to="/capabilities" className="btn btn-primary">
                Explore agents & tools
              </Link>
              <Link to="/how-it-works" className="btn btn-ghost">
                See the pipeline
              </Link>
              {signupOpen ? (
                <Link to="/signup" className="btn btn-ghost">
                  Start your organization
                </Link>
              ) : (
                <Link to="/login" className="btn btn-ghost">
                  Sign in to workspace
                </Link>
              )}
            </div>
            <p className="hero-note">
              {signupOpen === false
                ? "Self-service signup is disabled on this deployment. Sign in with credentials from your administrator."
                : signupOpen === null
                  ? "Checking availability…"
                  : "Sim mode works out of the box — connect live GitHub, GitLab, Jira, and AWS when you are ready."}
            </p>
          </div>
          <div className="hero-visual" aria-hidden="true">
            <div className="hero-panel hero-panel--agents">
              <div className="hero-panel-top">
                <span className="hero-panel-dots" />
                <span className="hero-panel-title">Live governance snapshot</span>
              </div>
              <div className="hero-agent-grid">
                {AGENTS.map((a) => (
                  <div key={a.id} className="hero-agent-chip">
                    <span className="hero-agent-name">{a.name}</span>
                    <span className="hero-agent-tag">{a.tagline}</span>
                  </div>
                ))}
              </div>
              <div className="hero-panel-metrics hero-panel-metrics--compact">
                <div className="hero-metric">
                  <span className="hero-metric-label">Global U</span>
                  <span className="hero-metric-value hero-metric-value--good">0.74</span>
                </div>
                <div className="hero-metric">
                  <span className="hero-metric-label">P / Ci / R</span>
                  <span className="hero-metric-value mono">0.68 / 0.61 / 0.82</span>
                </div>
                <div className="hero-metric">
                  <span className="hero-metric-label">Consensus</span>
                  <span className="hero-metric-value">0.71</span>
                </div>
              </div>
              <p className="hero-panel-caption">
                Illustrative output — each agent returns claim, confidence, evidence[], and tool signals.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="tech-strip" aria-label="Integrations and stack">
        <div className="tech-strip-inner">
          {TECH_STACK.map((tech) => (
            <span key={tech} className="tech-chip">
              {tech}
            </span>
          ))}
        </div>
      </section>

      <div className="trust-bar">
        <div className="trust-bar-inner">
          <span className="trust-item">
            <strong>17 weighted tools</strong> across CI, sprint, cost, and security
          </span>
          <span className="trust-sep" aria-hidden="true" />
          <span className="trust-item">
            <strong>PM-readable evidence</strong> — not just severity floats
          </span>
          <span className="trust-sep" aria-hidden="true" />
          <span className="trust-item">
            <strong>RAR re-grounding</strong> when consensus is low
          </span>
          <span className="trust-sep" aria-hidden="true" />
          <span className="trust-item">
            <strong>Audit-ready exports</strong> with cases, runs, and snapshots
          </span>
        </div>
      </div>

      <section id="agents" className="section">
        <p className="section-eyebrow">Domain agents</p>
        <h2 className="section-title">Spec-aligned agents with parallel tool execution</h2>
        <p className="section-lead">
          Each agent inherits a shared BaseAgent pattern: tools run concurrently, signals are weighted, staleness penalties
          apply, and human-readable evidence is packaged for PM review.
        </p>
        <div className="agent-showcase-grid">
          {AGENTS.map((agent) => (
            <article key={agent.id} className="agent-showcase-card">
              <div className="agent-showcase-head">
                <h3>{agent.name}</h3>
                <span className="agent-showcase-tag">{agent.tagline}</span>
              </div>
              <ul className="agent-tool-list">
                {agent.tools.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
              <p className="field-hint" style={{ margin: "0.65rem 0 0" }}>
                {agent.weight}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section id="integrations" className="section section-alt">
        <p className="section-eyebrow">Integrations</p>
        <h2 className="section-title">Live connectors your agents actually call</h2>
        <div className="integration-pill-grid">
          {INTEGRATIONS.map((item) => (
            <article key={item.name} className="integration-pill-card">
              <h3>{item.name}</h3>
              <p>{item.detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="pipeline" className="section">
        <div className="split-section">
          <div>
            <p className="section-eyebrow">Pipeline</p>
            <h2 className="section-title">From prompt to defensible decision</h2>
            <ol className="steps steps--enterprise">
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
          </div>
          <div className="integration-card pipeline-formula-card">
            <h3 className="integration-title">Utility formula</h3>
            <p className="pipeline-formula">U = 0.4 · P + 0.3 · Ci + 0.3 · R</p>
            <ul className="integration-list">
              <li>
                <strong>P</strong> — performance / delivery index from DevOps + PM agents
              </li>
              <li>
                <strong>Ci</strong> — FinOps cost-efficiency score from weighted cloud tools
              </li>
              <li>
                <strong>R</strong> — risk index from DevSecOps security signals
              </li>
            </ul>
            <p className="integration-note">
              FinOps cross-tool correlation boosts confidence when scaling anomalies coincide with spend spikes.
            </p>
          </div>
        </div>
      </section>

      <section id="enterprise" className="section">
        <div className="enterprise-band">
          <div>
            <p className="section-eyebrow section-eyebrow--on-dark">Workspace</p>
            <h2 className="enterprise-title">Everything after the agent run — in one tenant-scoped workspace</h2>
            <p className="enterprise-lead">
              Governance runs, incident intelligence, case approvals, evidence snapshots, portfolio linkage, and executive
              reports — built for engineering leaders and release managers who need proof, not platitudes.
            </p>
          </div>
          <ul className="enterprise-bullets">
            <li>Agent opinions with evidence[] and expandable tool signals in the UI</li>
            <li>GitHub and GitLab webhooks for fresher CI tool cache</li>
            <li>Multi-tenant RBAC, encrypted connector credentials, httpOnly session auth</li>
            <li>Signed share links and CSV/JSON exports for audit continuity</li>
          </ul>
        </div>
      </section>

      <section className="subpage-cta">
        <div className="subpage-cta-inner">
          <div className="subpage-cta-copy">
            <strong>See the four agents run on your next release review.</strong>
            <span>Explore capabilities, request access, or sign in to the workspace.</span>
          </div>
          <div className="subpage-cta-actions">
            <Link to="/request-access" className="btn btn-primary">
              Request access
            </Link>
            <Link to="/login" className="btn btn-ghost">
              Open workspace
            </Link>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
