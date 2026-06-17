import { useState } from "react";
import { Link } from "react-router-dom";
import { markOnboardingComplete } from "../lib/onboarding";

const STEPS = ["Connectors", "Test connection", "AI provider", "Confirm"] as const;

export function OnboardingWizardPage() {
  const [step, setStep] = useState(0);
  const [connectors, setConnectors] = useState({ github: true, gitlab: true, jira: true, finops: false });

  const finish = () => {
    markOnboardingComplete();
    setStep(STEPS.length - 1);
  };

  return (
    <div className="onboarding-page">
      <header className="gov-hub-header">
        <p className="gov-hub-eyebrow">Onboarding</p>
        <h1 className="gov-hub-title">Set up your workspace</h1>
        <p className="gov-hub-lead">Connect systems, validate health, and configure your default AI provider.</p>
      </header>
      <ol className="onboarding-steps">
        {STEPS.map((label, i) => (
          <li key={label} className={i === step ? "onboarding-step--active" : i < step ? "onboarding-step--done" : ""}>
            <span className="onboarding-step-index">{i + 1}</span>
            {label}
          </li>
        ))}
      </ol>
      {step === 0 ? (
        <div className="onboarding-panel card">
          <h2>Choose connectors</h2>
          <label className="onboarding-check">
            <input
              type="checkbox"
              checked={connectors.github}
              onChange={(e) => setConnectors((c) => ({ ...c, github: e.target.checked }))}
            />{" "}
            GitHub
          </label>
          <label className="onboarding-check">
            <input
              type="checkbox"
              checked={connectors.gitlab}
              onChange={(e) => setConnectors((c) => ({ ...c, gitlab: e.target.checked }))}
            />{" "}
            GitLab
          </label>
          <label className="onboarding-check">
            <input
              type="checkbox"
              checked={connectors.jira}
              onChange={(e) => setConnectors((c) => ({ ...c, jira: e.target.checked }))}
            />{" "}
            Jira
          </label>
          <label className="onboarding-check">
            <input
              type="checkbox"
              checked={connectors.finops}
              onChange={(e) => setConnectors((c) => ({ ...c, finops: e.target.checked }))}
            />{" "}
            FinOps / AWS
          </label>
          <p className="field-hint">
            Configure credentials in <Link to="/app/settings?tab=connectors">Settings → Connectors</Link>.
          </p>
        </div>
      ) : null}
      {step === 1 ? (
        <p className="onboarding-panel card">
          Connector test pings run from <Link to="/app/integrations">Integrations</Link> or Settings → Connectors.
        </p>
      ) : null}
      {step === 2 ? (
        <p className="onboarding-panel card">
          Configure your default LLM in <Link to="/app/settings?tab=ai">Settings → AI Providers</Link>.
        </p>
      ) : null}
      {step === 3 ? (
        <p className="onboarding-panel card">
          Ready to run governance. <Link to="/app/overview">Ask Casantris AI →</Link>
        </p>
      ) : null}
      <div className="onboarding-actions">
        <button type="button" className="btn btn-ghost" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
          Back
        </button>
        {step === STEPS.length - 1 ? (
          <Link to="/app/overview" className="btn btn-primary" onClick={markOnboardingComplete}>
            Finish
          </Link>
        ) : (
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              if (step === STEPS.length - 2) finish();
              else setStep((s) => Math.min(STEPS.length - 1, s + 1));
            }}
          >
            Next
          </button>
        )}
      </div>
    </div>
  );
}
