import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { markOnboardingComplete } from "../lib/onboarding";
import {
  saveConnectorConfigs,
  validateConnectorConfig,
  saveProviderConfigs,
} from "../api";

const STEPS = ["Connectors", "Test connections", "AI provider", "Confirm"] as const;
const CONNECTOR_NAMES = ["github", "gitlab", "jira", "finops"] as const;
const PROVIDERS = ["openai", "anthropic", "groq", "ollama"] as const;

export function OnboardingWizardPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Connector State
  const [connectors, setConnectors] = useState<Record<string, any>>({
    github: { enabled: false, config_json: { repo: "" }, credentials_json: { token: "" } },
    gitlab: { enabled: false, config_json: { gitlab_url: "", project_id: "" }, credentials_json: { token: "" } },
    jira: { enabled: false, config_json: { base_url: "", project: "", board_id: "" }, credentials_json: { email: "", token: "" } },
    finops: { enabled: false, config_json: { provider: "aws", cost_file_path: "" }, credentials_json: { aws_access_key_id: "", aws_secret_access_key: "" } },
  });

  const [testResults, setTestResults] = useState<Record<string, { status: "pending" | "success" | "error", message?: string }>>({});

  // Provider State
  const [defaultProvider, setDefaultProvider] = useState<string>("openai");
  const [providers, setProviders] = useState<Record<string, any>>({
    openai: { enabled: true, model_name: "gpt-4o", endpoint_url: "https://api.openai.com/v1", api_key_ref: "", credentials_json: { api_key: "" } },
    anthropic: { enabled: false, model_name: "claude-3-5-sonnet-latest", endpoint_url: "https://api.anthropic.com", api_key_ref: "", credentials_json: { api_key: "" } },
    groq: { enabled: false, model_name: "llama3-70b-8192", endpoint_url: "https://api.groq.com/openai/v1", api_key_ref: "", credentials_json: { api_key: "" } },
    ollama: { enabled: false, model_name: "llama3", endpoint_url: "http://localhost:11434/v1", api_key_ref: "", credentials_json: { api_key: "" } },
  });

  const handleNext = async () => {
    setError(null);
    if (step === 0) {
      setStep(1);
    } else if (step === 1) {
      setStep(2);
    } else if (step === 2) {
      setStep(3);
    } else if (step === STEPS.length - 1) {
      setSaving(true);
      try {
        await saveConnectorConfigs(connectors);
        await saveProviderConfigs({ default_provider: defaultProvider, providers });
        markOnboardingComplete();
        navigate("/app/overview");
      } catch (err: any) {
        setError(err.message || "Failed to complete onboarding");
      } finally {
        setSaving(false);
      }
    }
  };

  const runConnectorTests = async () => {
    setError(null);
    setSaving(true);
    
    try {
      await saveConnectorConfigs(connectors);
    } catch (err: any) {
      setError(err.message || "Failed to save connectors before testing");
      setSaving(false);
      return;
    }

    const enabledConnectors = Object.keys(connectors).filter(c => connectors[c].enabled);
    const newResults: typeof testResults = {};
    
    for (const name of enabledConnectors) {
      newResults[name] = { status: "pending" };
    }
    setTestResults({ ...newResults });

    for (const name of enabledConnectors) {
      try {
        await validateConnectorConfig(name);
        newResults[name] = { status: "success" };
      } catch (err: any) {
        newResults[name] = { status: "error", message: err.message };
      }
      setTestResults({ ...newResults });
    }
    setSaving(false);
  };

  const renderConnectorForm = (name: string) => {
    const draft = connectors[name];
    if (!draft.enabled) return null;
    
    const updateConfig = (key: string, val: string) => setConnectors(prev => ({ ...prev, [name]: { ...prev[name], config_json: { ...prev[name].config_json, [key]: val } } }));
    const updateCreds = (key: string, val: string) => setConnectors(prev => ({ ...prev, [name]: { ...prev[name], credentials_json: { ...prev[name].credentials_json, [key]: val } } }));

    if (name === "github") {
      return (
        <div className="config-columns settings-quick-grid" style={{ marginTop: "1rem" }}>
          <div className="form-row"><label>Repository</label><input value={draft.config_json.repo} onChange={e => updateConfig("repo", e.target.value)} placeholder="owner/repo" /></div>
          <div className="form-row"><label>GitHub token (PAT)</label><input type="password" value={draft.credentials_json.token} onChange={e => updateCreds("token", e.target.value)} placeholder="ghp_..." /></div>
        </div>
      );
    }
    if (name === "gitlab") {
      return (
        <div className="config-columns settings-quick-grid" style={{ marginTop: "1rem" }}>
          <div className="form-row"><label>GitLab URL</label><input value={draft.config_json.gitlab_url} onChange={e => updateConfig("gitlab_url", e.target.value)} placeholder="https://gitlab.com" /></div>
          <div className="form-row"><label>Project ID</label><input value={draft.config_json.project_id} onChange={e => updateConfig("project_id", e.target.value)} placeholder="owner/repo" /></div>
          <div className="form-row"><label>Access Token</label><input type="password" value={draft.credentials_json.token} onChange={e => updateCreds("token", e.target.value)} placeholder="glpat-..." /></div>
        </div>
      );
    }
    if (name === "jira") {
      return (
        <div className="config-columns settings-quick-grid" style={{ marginTop: "1rem" }}>
          <div className="form-row"><label>Jira Base URL</label><input value={draft.config_json.base_url} onChange={e => updateConfig("base_url", e.target.value)} placeholder="https://domain.atlassian.net" /></div>
          <div className="form-row"><label>Project Key</label><input value={draft.config_json.project} onChange={e => updateConfig("project", e.target.value)} placeholder="PROJ" /></div>
          <div className="form-row"><label>Account Email</label><input value={draft.credentials_json.email} onChange={e => updateCreds("email", e.target.value)} placeholder="you@company.com" /></div>
          <div className="form-row"><label>API Token</label><input type="password" value={draft.credentials_json.token} onChange={e => updateCreds("token", e.target.value)} placeholder="Enter token" /></div>
        </div>
      );
    }
    if (name === "finops") {
      return (
        <div className="config-columns settings-quick-grid" style={{ marginTop: "1rem" }}>
          <div className="form-row"><label>Cost File Path</label><input value={draft.config_json.cost_file_path} onChange={e => updateConfig("cost_file_path", e.target.value)} placeholder="s3://..." /></div>
          <div className="form-row"><label>AWS Access Key</label><input value={draft.credentials_json.aws_access_key_id} onChange={e => updateCreds("aws_access_key_id", e.target.value)} /></div>
          <div className="form-row"><label>AWS Secret Key</label><input type="password" value={draft.credentials_json.aws_secret_access_key} onChange={e => updateCreds("aws_secret_access_key", e.target.value)} /></div>
        </div>
      );
    }
    return null;
  };

  const renderProviderForm = (name: string) => {
    const draft = providers[name];
    if (!draft.enabled) return null;
    
    const updateDraft = (key: string, val: string) => setProviders(prev => ({ ...prev, [name]: { ...prev[name], [key]: val } }));
    const updateCreds = (key: string, val: string) => setProviders(prev => ({ ...prev, [name]: { ...prev[name], credentials_json: { ...prev[name].credentials_json, [key]: val } } }));

    return (
      <div className="config-columns settings-quick-grid" style={{ marginTop: "1rem" }}>
        <div className="form-row"><label>Model Name</label><input value={draft.model_name} onChange={e => updateDraft("model_name", e.target.value)} /></div>
        <div className="form-row"><label>Endpoint URL</label><input value={draft.endpoint_url} onChange={e => updateDraft("endpoint_url", e.target.value)} /></div>
        <div className="form-row"><label>API Key</label><input type="password" value={draft.credentials_json.api_key} onChange={e => updateCreds("api_key", e.target.value)} placeholder="sk-..." /></div>
      </div>
    );
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

      {error && <div className="alert alert-danger" style={{ marginBottom: "1rem", color: "var(--danger-color)" }}>{error}</div>}

      {step === 0 ? (
        <div className="onboarding-panel card">
          <h2>Choose and configure connectors</h2>
          <p className="field-hint" style={{ marginBottom: "1rem" }}>Enable the systems you use and provide access credentials.</p>
          {CONNECTOR_NAMES.map(name => (
            <div key={name} style={{ marginBottom: "1.5rem", paddingBottom: "1.5rem", borderBottom: "1px solid var(--border-color)" }}>
              <label className="onboarding-check" style={{ fontWeight: "bold", fontSize: "1.1rem", textTransform: "capitalize" }}>
                <input
                  type="checkbox"
                  checked={connectors[name].enabled}
                  onChange={(e) => setConnectors((c) => ({ ...c, [name]: { ...c[name], enabled: e.target.checked } }))}
                />{" "}
                {name}
              </label>
              {renderConnectorForm(name)}
            </div>
          ))}
        </div>
      ) : null}

      {step === 1 ? (
        <div className="onboarding-panel card">
          <h2>Test connections</h2>
          <p className="field-hint" style={{ marginBottom: "1rem" }}>We will ping the APIs of the connectors you enabled to ensure credentials are correct.</p>
          
          <button type="button" className="btn btn-secondary" onClick={runConnectorTests} disabled={saving}>
            {saving ? "Testing..." : "Run Tests"}
          </button>

          <div style={{ marginTop: "2rem" }}>
            {Object.keys(connectors).filter(c => connectors[c].enabled).map(name => (
              <div key={name} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid var(--border-color)" }}>
                <span style={{ textTransform: "capitalize", fontWeight: "bold" }}>{name}</span>
                <span>
                  {!testResults[name] && <span style={{ color: "var(--text-muted)" }}>Not tested</span>}
                  {testResults[name]?.status === "pending" && <span style={{ color: "var(--primary-color)" }}>Testing...</span>}
                  {testResults[name]?.status === "success" && <span style={{ color: "var(--success-color)" }}>Success ✓</span>}
                  {testResults[name]?.status === "error" && <span style={{ color: "var(--danger-color)" }}>Failed: {testResults[name].message}</span>}
                </span>
              </div>
            ))}
            {Object.keys(connectors).filter(c => connectors[c].enabled).length === 0 && (
              <p className="field-hint">No connectors enabled.</p>
            )}
          </div>
        </div>
      ) : null}

      {step === 2 ? (
        <div className="onboarding-panel card">
          <h2>Configure AI Provider</h2>
          <p className="field-hint" style={{ marginBottom: "1rem" }}>Choose the default LLM provider for governance runs.</p>
          
          <div className="form-row">
            <label className="field-label-required">Default Provider</label>
            <select
              value={defaultProvider}
              onChange={(e) => {
                setDefaultProvider(e.target.value);
                setProviders(p => {
                  const np = { ...p };
                  Object.keys(np).forEach(k => np[k].enabled = false);
                  if (e.target.value) np[e.target.value].enabled = true;
                  return np;
                });
              }}
            >
              <option value="">Select a provider</option>
              {PROVIDERS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          {defaultProvider && (
            <div style={{ marginTop: "2rem", paddingTop: "2rem", borderTop: "1px solid var(--border-color)" }}>
              <h3 style={{ textTransform: "capitalize", marginBottom: "1rem" }}>{defaultProvider} Settings</h3>
              {renderProviderForm(defaultProvider)}
            </div>
          )}
        </div>
      ) : null}

      {step === 3 ? (
        <div className="onboarding-panel card">
          <h2>Confirm Setup</h2>
          <p className="field-hint" style={{ marginBottom: "1rem" }}>You are ready to run governance! Click "Complete Setup" to save your configurations and enter your workspace.</p>
          
          <div style={{ background: "var(--bg-subtle)", padding: "1rem", borderRadius: "6px" }}>
            <h4>Summary</h4>
            <ul style={{ marginTop: "0.5rem", paddingLeft: "1.5rem" }}>
              <li><strong>Connectors:</strong> {Object.keys(connectors).filter(c => connectors[c].enabled).join(", ") || "None"}</li>
              <li><strong>AI Provider:</strong> {defaultProvider || "None"}</li>
            </ul>
          </div>
        </div>
      ) : null}

      <div className="onboarding-actions">
        <button type="button" className="btn btn-ghost" disabled={step === 0 || saving} onClick={() => setStep((s) => s - 1)}>
          Back
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleNext}
          disabled={saving}
        >
          {saving ? "Saving..." : step === STEPS.length - 1 ? "Complete Setup" : "Next"}
        </button>
      </div>
    </div>
  );
}
