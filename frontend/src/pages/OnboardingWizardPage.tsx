import { useState } from "react";
import { Link } from "react-router-dom";

const STEPS = ["Connectors", "Test connection", "AI provider", "Confirm"] as const;

export function OnboardingWizardPage() {
  const [step, setStep] = useState(0);
  const [connectors, setConnectors] = useState({ github: true, jira: true, finops: false });

  return (
    <div className="app onboarding-page">
      <header className="gov-hub-header">
        <p className="gov-hub-eyebrow">Onboarding</p>
        <h1 className="gov-hub-title">Set up your workspace</h1>
      </header>
      <ol className="onboarding-steps">
        {STEPS.map((label, i) => (
          <li key={label} className={i === step ? "onboarding-step--active" : ""}>
            {label}
          </li>
        ))}
      </ol>
      {step === 0 ? (
        <div className="onboarding-panel">
          <label>
            <input
              type="checkbox"
              checked={connectors.github}
              onChange={(e) => setConnectors((c) => ({ ...c, github: e.target.checked }))}
            />{" "}
            GitHub
          </label>
          <label>
            <input
              type="checkbox"
              checked={connectors.jira}
              onChange={(e) => setConnectors((c) => ({ ...c, jira: e.target.checked }))}
            />{" "}
            Jira
          </label>
          <label>
            <input
              type="checkbox"
              checked={connectors.finops}
              onChange={(e) => setConnectors((c) => ({ ...c, finops: e.target.checked }))}
            />{" "}
            FinOps / AWS
          </label>
        </div>
      ) : null}
      {step === 1 ? <p className="onboarding-panel">Connector test pings run from Settings → Integrations.</p> : null}
      {step === 2 ? <p className="onboarding-panel">Configure your default LLM in AI Config.</p> : null}
      {step === 3 ? (
        <p className="onboarding-panel">
          Ready to run governance. <Link to="/app/overview">Ask Casantris AI →</Link>
        </p>
      ) : null}
      <div className="onboarding-actions">
        <button type="button" className="btn btn-ghost" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
          Back
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setStep((s) => Math.min(STEPS.length - 1, s + 1))}
        >
          {step === STEPS.length - 1 ? "Finish" : "Next"}
        </button>
      </div>
    </div>
  );
}
