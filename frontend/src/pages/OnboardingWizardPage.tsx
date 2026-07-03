import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { markOnboardingComplete } from "../lib/onboarding";
import {
  fetchConnectorConfigs,
  saveConnectorConfigs,
  validateConnectorConfig,
  saveProviderConfigs,
  fetchGitHubReposApi,
  fetchGitHubBranchesApi,
  fetchJiraProjectsApi,
  fetchJiraBoardsApi,
} from "../api";

const STEPS = ["Connection Setup", "Test Connection", "Summary"] as const;

interface SearchableMultiSelectProps {
  label: string;
  helperText?: string;
  searchPlaceholder?: string;
  items: any[];
  selectedKeys: string[];
  onChange: (keys: string[]) => void;
  getOptionLabel: (item: any) => string;
  getOptionKey: (item: any) => string;
  getOptionSublabel?: (item: any) => string;
  iconType: "repo" | "branch" | "project" | "board";
  loading?: boolean;
  searchQuery: string;
  setSearchQuery: (q: string) => void;
}

function SearchableMultiSelect({
  label,
  helperText,
  searchPlaceholder = "Search...",
  items,
  selectedKeys,
  onChange,
  getOptionLabel,
  getOptionKey,
  getOptionSublabel,
  iconType,
  loading = false,
  searchQuery,
  setSearchQuery,
}: SearchableMultiSelectProps) {
  const renderIcon = (item: any, key: string, name: string) => {
    if (iconType === "repo") {
      return (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3z"/>
          <path d="M6 2v12"/>
        </svg>
      );
    }
    if (iconType === "branch") {
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="18" cy="18" r="3" />
          <circle cx="6" cy="6" r="3" />
          <circle cx="6" cy="18" r="3" />
          <path d="M18 15V9a4 4 0 0 0-4-4H9" />
          <line x1="6" y1="9" x2="6" y2="15" />
        </svg>
      );
    }
    if (iconType === "project") {
      const colors = ["#2563eb", "#10b981", "#8b5cf6", "#f59e0b", "#ec4899", "#14b8a6"];
      let sum = 0;
      for (let i = 0; i < key.length; i++) sum += key.charCodeAt(i);
      const color = colors[sum % colors.length];
      return (
        <div style={{
          width: "22px",
          height: "22px",
          borderRadius: "5px",
          background: color,
          color: "#fff",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "0.7rem",
          fontWeight: "bold"
        }}>
          {key.charAt(0).toUpperCase()}
        </div>
      );
    }
    if (iconType === "board") {
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
          <line x1="9" y1="3" x2="9" y2="21"/>
          <line x1="15" y1="3" x2="15" y2="21"/>
        </svg>
      );
    }
    return null;
  };

  const handleToggle = (key: string) => {
    if (selectedKeys.includes(key)) {
      onChange(selectedKeys.filter(k => k !== key));
    } else {
      onChange([...selectedKeys, key]);
    }
  };

  return (
    <div className="searchable-select form-row" style={{ gridColumn: "span 2" }}>
      <label className="field-label-required" style={{ marginBottom: "0.2rem", fontWeight: "600", fontSize: "0.95rem" }}>{label}</label>
      {helperText && <p className="field-hint" style={{ marginTop: 0, marginBottom: "0.6rem", fontSize: "0.82rem", color: "var(--muted)", opacity: 0.9 }}>{helperText}</p>}
      
      {selectedKeys.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "0.75rem" }}>
          {selectedKeys.map(key => {
            const item = items.find(i => getOptionKey(i) === key);
            const labelStr = item ? getOptionLabel(item) : key;
            return (
              <span key={key} style={{
                background: "var(--primary-color)", color: "#fff", padding: "0.25rem 0.6rem", 
                borderRadius: "16px", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "0.4rem"
              }}>
                {labelStr}
                <button type="button" onClick={() => handleToggle(key)} style={{
                  background: "transparent", border: "none", color: "#fff", cursor: "pointer", 
                  padding: 0, display: "flex", alignItems: "center", opacity: 0.8
                }}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </span>
            );
          })}
        </div>
      )}

      <div className="searchable-select-input-wrapper">
        <span className="searchable-select-search-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </span>
        <input
          type="text"
          className="searchable-select-input"
          placeholder={searchPlaceholder}
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
        />
        {searchQuery && (
          <button
            type="button"
            className="searchable-select-clear-btn"
            onClick={() => setSearchQuery("")}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        )}
      </div>

      <div className="searchable-select-list">
        {loading ? (
          <div style={{ padding: "1.25rem", textAlign: "center", color: "var(--muted)", fontSize: "0.85rem" }}>
            Loading options from backend...
          </div>
        ) : items.length === 0 ? (
          <div style={{ padding: "1.25rem", textAlign: "center", color: "var(--muted)", fontSize: "0.85rem" }}>
            No matching options found
          </div>
        ) : (
          items.map(item => {
            const key = getOptionKey(item);
            const labelStr = getOptionLabel(item);
            const sublabel = getOptionSublabel ? getOptionSublabel(item) : undefined;
            const isSelected = selectedKeys.includes(key);

            return (
              <div
                key={key}
                className={`searchable-select-item ${isSelected ? "searchable-select-item--selected" : ""}`}
                onClick={() => handleToggle(key)}
              >
                <div className="searchable-select-item-content">
                  <span className="searchable-select-item-icon">
                    {renderIcon(item, key, labelStr)}
                  </span>
                  <div className="searchable-select-item-details">
                    <span className="searchable-select-item-title">{labelStr}</span>
                    {sublabel && <span className="searchable-select-item-sublabel">{sublabel}</span>}
                  </div>
                </div>
                {isSelected && (
                  <span style={{ color: "var(--success)", fontWeight: "bold", fontSize: "0.95rem", paddingRight: "0.3rem" }}>
                    ✓
                  </span>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

export function OnboardingWizardPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Lists loaded from backend APIs
  const [repos, setRepos] = useState<string[]>([]);
  const [branches, setBranches] = useState<string[]>([]);
  const [jiraProjects, setJiraProjects] = useState<{ key: string; name: string }[]>([]);
  const [jiraBoards, setJiraBoards] = useState<{ id: string; name: string; type: string }[]>([]);
  const [gitlabProjects, setGitLabProjects] = useState<{ id: string; name: string }[]>([]);
  const [gitlabBranches, setGitLabBranches] = useState<string[]>([]);
  const [finopsProviders, setFinopsProviders] = useState<{ key: string; name: string }[]>([]);
  const [finopsProfiles, setFinopsProfiles] = useState<{ id: string; name: string }[]>([]);

  // Loading states
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [loadingBranches, setLoadingBranches] = useState(false);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [loadingBoards, setLoadingBoards] = useState(false);
  const [loadingGitLabProjects, setLoadingGitLabProjects] = useState(false);
  const [loadingGitLabBranches, setLoadingGitLabBranches] = useState(false);
  const [loadingFinopsProviders, setLoadingFinopsProviders] = useState(false);
  const [loadingFinopsProfiles, setLoadingFinopsProfiles] = useState(false);

  // Search filter states
  const [repoSearch, setRepoSearch] = useState("");
  const [branchSearch, setBranchSearch] = useState("");
  const [projectSearch, setProjectSearch] = useState("");
  const [boardSearch, setBoardSearch] = useState("");
  const [gitlabProjectSearch, setGitLabProjectSearch] = useState("");
  const [gitlabBranchSearch, setGitLabBranchSearch] = useState("");
  const [finopsProviderSearch, setFinopsProviderSearch] = useState("");
  const [finopsProfileSearch, setFinopsProfileSearch] = useState("");

  // Connector State
  const [connectors, setConnectors] = useState<Record<string, any>>({
    github: { enabled: false, config_json: { repos: [], release_branches: ["main"] }, credentials_json: {} },
    jira: { enabled: false, config_json: { base_url: "", projects: [], board_ids: [] }, credentials_json: {} },
    gitlab: { enabled: false, config_json: { gitlab_url: "", project_ids: [], release_branches: [] }, credentials_json: {} },
    finops: { enabled: false, config_json: { providers: ["aws"], cost_file_paths: [] }, credentials_json: {} },
  });

  const [testResults, setTestResults] = useState<Record<string, { status: "pending" | "success" | "error", message?: string }>>({});

  // Default silent Provider State (saved on final step)
  const defaultProvider = "openai";
  const providers: Record<string, any> = {
    openai: { enabled: true, model_name: "gpt-4o", endpoint_url: "https://api.openai.com/v1", api_key_ref: "", credentials_json: { api_key: "" } },
    anthropic: { enabled: false, model_name: "claude-3-5-sonnet-latest", endpoint_url: "https://api.anthropic.com", api_key_ref: "", credentials_json: { api_key: "" } },
    ollama: { enabled: false, model_name: "llama3", endpoint_url: "http://localhost:11434/v1", api_key_ref: "", credentials_json: { api_key: "" } },
  };

  // Load existing configurations from settings on mount
  useEffect(() => {
    const initOnboarding = async () => {
      try {
        const configs = await fetchConnectorConfigs();
        const nextConnectors = { ...connectors };
        
        configs.forEach((c) => {
          if (nextConnectors[c.connector_name]) {
            nextConnectors[c.connector_name] = {
              enabled: c.enabled,
              config_json: c.config_json || {},
              credentials_json: {}, // Keep credentials empty to prevent overwriting
            };
          }
        });
        
        setConnectors(nextConnectors);

        // Fetch dynamic details if already enabled in settings
        if (nextConnectors.github.enabled) {
          loadGitHubRepos();
        }
        if (nextConnectors.jira.enabled) {
          loadJiraProjects();
        }
        if (nextConnectors.gitlab.enabled) {
          loadGitLabProjects();
        }
        if (nextConnectors.finops.enabled) {
          loadFinopsProviders();
          loadFinopsProfiles(nextConnectors.finops.config_json.provider || "aws");
        }
      } catch (err: any) {
        setError("Failed to fetch initial settings configurations from backend.");
      }
    };
    initOnboarding();
  }, []);

  const loadGitHubRepos = async () => {
    setLoadingRepos(true);
    setError(null);
    try {
      const data = await fetchGitHubReposApi();
      setRepos(data);
      if (data.length > 0) {
        const currentRepo = connectors.github.config_json.repo || data[0];
        if (!connectors.github.config_json.repo) {
          setConnectors(prev => ({
            ...prev,
            github: {
              ...prev.github,
              config_json: { ...prev.github.config_json, repo: currentRepo }
            }
          }));
        }
        loadGitHubBranches(currentRepo);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load GitHub repositories. Check your Settings.");
    } finally {
      setLoadingRepos(false);
    }
  };

  const loadGitHubBranches = async (repo: string) => {
    if (!repo) return;
    setLoadingBranches(true);
    setError(null);
    try {
      const data = await fetchGitHubBranchesApi(repo);
      setBranches(data);
      if (data.length > 0) {
        const currentBranch = connectors.github.config_json.release_branch || (data.includes("main") ? "main" : data.includes("master") ? "master" : data[0]);
        setConnectors(prev => ({
          ...prev,
          github: {
            ...prev.github,
            config_json: { ...prev.github.config_json, release_branch: currentBranch }
          }
        }));
      }
    } catch (err: any) {
      setError(err.message || "Failed to load branches.");
    } finally {
      setLoadingBranches(false);
    }
  };

  const loadJiraProjects = async () => {
    setLoadingProjects(true);
    setError(null);
    try {
      const data = await fetchJiraProjectsApi();
      setJiraProjects(data);
      if (data.length > 0) {
        const currentProject = connectors.jira.config_json.project || data[0].key;
        if (!connectors.jira.config_json.project) {
          setConnectors(prev => ({
            ...prev,
            jira: {
              ...prev.jira,
              config_json: { ...prev.jira.config_json, project: currentProject }
            }
          }));
        }
        loadJiraBoards(currentProject);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load Jira projects. Check your Settings.");
    } finally {
      setLoadingProjects(false);
    }
  };

  const loadJiraBoards = async (projectKey: string) => {
    if (!projectKey) return;
    setLoadingBoards(true);
    setError(null);
    try {
      const data = await fetchJiraBoardsApi(projectKey);
      setJiraBoards(data);
      if (data.length > 0) {
        const currentBoard = connectors.jira.config_json.board_id || data[0].id;
        setConnectors(prev => ({
          ...prev,
          jira: {
            ...prev.jira,
            config_json: { ...prev.jira.config_json, board_id: currentBoard }
          }
        }));
      }
    } catch (err: any) {
      setError(err.message || "Failed to load Jira boards.");
    } finally {
      setLoadingBoards(false);
    }
  };

  const loadGitLabProjects = async () => {
    setLoadingGitLabProjects(true);
    setError(null);
    try {
      await new Promise(res => setTimeout(res, 500));
      const data = [
        { id: "gitlab-org/gitlab", name: "GitLab HQ" },
        { id: "my-company/frontend", name: "Frontend Portal" },
        { id: "my-company/backend", name: "Core API" }
      ];
      setGitLabProjects(data);
      if (data.length > 0 && !connectors.gitlab.config_json.project_id) {
        setConnectors(prev => ({
          ...prev, gitlab: { ...prev.gitlab, config_json: { ...prev.gitlab.config_json, project_id: data[0].id } }
        }));
        loadGitLabBranches(data[0].id);
      } else if (connectors.gitlab.config_json.project_id) {
        loadGitLabBranches(connectors.gitlab.config_json.project_id);
      }
    } catch (err: any) {
      setError("Failed to load GitLab projects.");
    } finally {
      setLoadingGitLabProjects(false);
    }
  };

  const loadGitLabBranches = async (projectId: string) => {
    if (!projectId) return;
    setLoadingGitLabBranches(true);
    try {
      await new Promise(res => setTimeout(res, 400));
      setGitLabBranches(["main", "develop", "feature/auth", "release/v1"]);
    } finally {
      setLoadingGitLabBranches(false);
    }
  };

  const loadFinopsProviders = async () => {
    setLoadingFinopsProviders(true);
    try {
      await new Promise(res => setTimeout(res, 200));
      const data = [
        { key: "aws", name: "Amazon Web Services (AWS)" },
        { key: "gcp", name: "Google Cloud Platform (GCP)" },
        { key: "azure", name: "Microsoft Azure" }
      ];
      setFinopsProviders(data);
    } finally {
      setLoadingFinopsProviders(false);
    }
  };

  const loadFinopsProfiles = async (provider: string) => {
    if (!provider) return;
    setLoadingFinopsProfiles(true);
    try {
      await new Promise(res => setTimeout(res, 300));
      const data = provider === "aws" 
        ? [{ id: "cost-report-1", name: "Production Billing Report" }, { id: "cost-report-2", name: "Staging Cur" }]
        : [{ id: "billing-1", name: "Main Billing Account" }];
      setFinopsProfiles(data);
    } finally {
      setLoadingFinopsProfiles(false);
    }
  };

  const handleToggle = (name: string, enabled: boolean) => {
    setConnectors(prev => ({
      ...prev,
      [name]: { ...prev[name], enabled }
    }));
    if (enabled) {
      if (name === "github" && repos.length === 0) {
        loadGitHubRepos();
      }
      if (name === "jira" && jiraProjects.length === 0) {
        loadJiraProjects();
      }
    }
  };

  const handleNext = async () => {
    setError(null);
    if (step === 0) {
      if (connectors.github.enabled && !connectors.github.config_json.repo) {
        setError("Please select a GitHub repository.");
        return;
      }
      if (connectors.jira.enabled && (!connectors.jira.config_json.base_url || !connectors.jira.config_json.project)) {
        setError("Please ensure JIRA Base URL and Project are selected.");
        return;
      }
      setStep(1);
    } else if (step === 1) {
      setStep(2);
    } else if (step === STEPS.length - 1) {
      setSaving(true);
      try {
        const connectorsToSave: Record<string, any> = {};
        Object.keys(connectors).forEach(key => {
          connectorsToSave[key] = {
            enabled: connectors[key].enabled,
            config_json: connectors[key].config_json,
            credentials_json: {},
          };
        });

        // Silently save default provider config so the AI is ready
        const providersToSave: Record<string, any> = {};
        Object.keys(providers).forEach(key => {
          providersToSave[key] = {
            enabled: providers[key].enabled,
            model_name: providers[key].model_name,
            endpoint_url: providers[key].endpoint_url,
            api_key: providers[key].credentials_json?.api_key || null,
          };
        });
        await saveProviderConfigs({ default_provider: defaultProvider, providers: providersToSave });
        
        await saveConnectorConfigs(connectorsToSave);
        markOnboardingComplete();
        navigate("/app/overview");
      } catch (err: any) {
        setError(err.message || "Failed to complete onboarding setup.");
      } finally {
        setSaving(false);
      }
    }
  };

  const runConnectorTests = async () => {
    setError(null);
    setSaving(true);

    const connectorsToSave: Record<string, any> = {};
    Object.keys(connectors).forEach(key => {
      connectorsToSave[key] = {
        enabled: connectors[key].enabled,
        config_json: connectors[key].config_json,
        credentials_json: {},
      };
    });
    
    try {
      await saveConnectorConfigs(connectorsToSave);
    } catch (err: any) {
      setError(err.message || "Failed to save connector configurations before testing.");
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

  // Filter lists based on search inputs
  const getFilteredGitHubRepos = () => {
    const draft = connectors.github;
    const selectedRepos = draft.config_json.repos || [];
    const filtered = repos.filter(r => r.toLowerCase().includes(repoSearch.toLowerCase()));
    selectedRepos.forEach((r: string) => {
      if (!filtered.includes(r)) filtered.unshift(r);
    });
    return filtered;
  };

  const getFilteredGitHubBranches = () => {
    const draft = connectors.github;
    const selectedBranches = draft.config_json.release_branches || ["main"];
    const filtered = branches.filter(b => b.toLowerCase().includes(branchSearch.toLowerCase()));
    selectedBranches.forEach((b: string) => {
      if (!filtered.includes(b)) filtered.unshift(b);
    });
    return filtered;
  };

  const getFilteredJiraProjects = () => {
    const draft = connectors.jira;
    const selectedProjects = draft.config_json.projects || [];
    const filtered = jiraProjects.filter(p => 
      p.name.toLowerCase().includes(projectSearch.toLowerCase()) || 
      p.key.toLowerCase().includes(projectSearch.toLowerCase())
    );
    selectedProjects.forEach((proj: string) => {
      const projObj = jiraProjects.find(p => p.key === proj);
      if (projObj && !filtered.some(p => p.key === proj)) filtered.unshift(projObj);
    });
    return filtered;
  };

  const getFilteredJiraBoards = () => {
    const draft = connectors.jira;
    const selectedBoards = draft.config_json.board_ids || [];
    const filtered = jiraBoards.filter(b => b.name.toLowerCase().includes(boardSearch.toLowerCase()));
    selectedBoards.forEach((boardId: string) => {
      const boardObj = jiraBoards.find(b => b.id === boardId);
      if (boardObj && !filtered.some(b => b.id === boardId)) filtered.unshift(boardObj);
    });
    return filtered;
  };

  const getFilteredGitLabProjects = () => {
    const draft = connectors.gitlab;
    const selectedProjects = draft.config_json.project_ids || [];
    const filtered = gitlabProjects.filter(p => p.name.toLowerCase().includes(gitlabProjectSearch.toLowerCase()) || p.id.toLowerCase().includes(gitlabProjectSearch.toLowerCase()));
    selectedProjects.forEach((proj: string) => {
      const projObj = gitlabProjects.find(p => p.id === proj);
      if (projObj && !filtered.some(p => p.id === proj)) filtered.unshift(projObj);
    });
    return filtered;
  };

  const getFilteredGitLabBranches = () => {
    const draft = connectors.gitlab;
    const selectedBranches = draft.config_json.release_branches || ["main"];
    const filtered = gitlabBranches.filter(b => b.toLowerCase().includes(gitlabBranchSearch.toLowerCase()));
    selectedBranches.forEach((b: string) => {
      if (!filtered.includes(b)) filtered.unshift(b);
    });
    return filtered;
  };

  const getFilteredFinopsProviders = () => {
    const draft = connectors.finops;
    const selectedProviders = draft.config_json.providers || ["aws"];
    const filtered = finopsProviders.filter(p => p.name.toLowerCase().includes(finopsProviderSearch.toLowerCase()) || p.key.toLowerCase().includes(finopsProviderSearch.toLowerCase()));
    selectedProviders.forEach((prov: string) => {
      const pObj = finopsProviders.find(p => p.key === prov);
      if (pObj && !filtered.some(p => p.key === prov)) filtered.unshift(pObj);
    });
    return filtered;
  };

  const getFilteredFinopsProfiles = () => {
    const draft = connectors.finops;
    const selectedProfiles = draft.config_json.cost_file_paths || [];
    const filtered = finopsProfiles.filter(p => p.name.toLowerCase().includes(finopsProfileSearch.toLowerCase()));
    selectedProfiles.forEach((prof: string) => {
      const pObj = finopsProfiles.find(p => p.id === prof);
      if (pObj && !filtered.some(p => p.id === prof)) filtered.unshift(pObj);
    });
    return filtered;
  };

  const renderConnectorForm = (name: string) => {
    const draft = connectors[name];
    if (!draft.enabled) return null;
    
    const updateConfig = (key: string, val: string) => setConnectors(prev => ({ ...prev, [name]: { ...prev[name], config_json: { ...prev[name].config_json, [key]: val } } }));

    if (name === "github") {
      return (
        <div className="config-columns settings-quick-grid" style={{ marginTop: "1rem" }}>
          <SearchableMultiSelect
            label="Which code projects are you working on?"
            helperText="Select the GitHub repositories containing your application's source code."
            searchPlaceholder="Search / filter repositories..."
            items={getFilteredGitHubRepos()}
            selectedKeys={draft.config_json.repos || []}
            onChange={(repos) => {
              updateConfig("repos", repos);
              if (repos.length > 0) loadGitHubBranches(repos[0]);
            }}
            getOptionKey={(r) => r}
            getOptionLabel={(r) => r}
            getOptionSublabel={(r) => (draft.config_json.repos || []).includes(r) ? "Active repository selection" : "GitHub code repository"}
            iconType="repo"
            loading={loadingRepos}
            searchQuery={repoSearch}
            setSearchQuery={setRepoSearch}
          />

          <SearchableMultiSelect
            label="Which versions/branches are these for?"
            helperText="Select the branches to monitor for releases and updates (usually 'main' or 'master')."
            searchPlaceholder="Search / filter branches..."
            items={getFilteredGitHubBranches()}
            selectedKeys={draft.config_json.release_branches || []}
            onChange={(branches) => updateConfig("release_branches", branches)}
            getOptionKey={(b) => b}
            getOptionLabel={(b) => b}
            getOptionSublabel={(b) => (draft.config_json.release_branches || []).includes(b) ? "Selected release branch" : "Git repository branch"}
            iconType="branch"
            loading={loadingBranches}
            searchQuery={branchSearch}
            setSearchQuery={setBranchSearch}
          />
        </div>
      );
    }

    if (name === "jira") {
      return (
        <div className="config-columns settings-quick-grid" style={{ marginTop: "1rem" }}>
          <SearchableMultiSelect
            label="Which Jira projects are you connecting?"
            helperText="Select the projects from your Jira instance where issues are tracked."
            searchPlaceholder="Search / filter projects..."
            items={getFilteredJiraProjects()}
            selectedKeys={draft.config_json.projects || []}
            onChange={(projKeys) => {
              updateConfig("projects", projKeys);
              if (projKeys.length > 0) loadJiraBoards(projKeys[0]);
            }}
            getOptionKey={(p) => p.key}
            getOptionLabel={(p) => p.name}
            getOptionSublabel={(p) => `Project Key: ${p.key}`}
            iconType="project"
            loading={loadingProjects}
            searchQuery={projectSearch}
            setSearchQuery={setProjectSearch}
          />

          <SearchableMultiSelect
            label="Which Jira boards are you connecting?"
            helperText="Select the active boards for monitoring sprint tickets and sprint blockers."
            searchPlaceholder="Search / filter boards..."
            items={getFilteredJiraBoards()}
            selectedKeys={draft.config_json.board_ids || []}
            onChange={(boardIds) => updateConfig("board_ids", boardIds)}
            getOptionKey={(b) => b.id}
            getOptionLabel={(b) => b.name}
            getOptionSublabel={(b) => `Agile ${b.type} board (ID: ${b.id})`}
            iconType="board"
            loading={loadingBoards}
            searchQuery={boardSearch}
            setSearchQuery={setBoardSearch}
          />
        </div>
      );
    }

    if (name === "gitlab") {
      return (
        <div className="config-columns settings-quick-grid" style={{ marginTop: "1rem" }}>
          <SearchableMultiSelect
            label="Which GitLab projects are you working on?"
            helperText="Select the GitLab repositories containing your application's source code."
            searchPlaceholder="Search / filter projects..."
            items={getFilteredGitLabProjects()}
            selectedKeys={draft.config_json.project_ids || []}
            onChange={(projectIds) => {
              updateConfig("project_ids", projectIds);
              if (projectIds.length > 0) loadGitLabBranches(projectIds[0]);
            }}
            getOptionKey={(p) => p.id}
            getOptionLabel={(p) => p.name}
            getOptionSublabel={(p) => (draft.config_json.project_ids || []).includes(p.id) ? "Active project selection" : "GitLab project"}
            iconType="repo"
            loading={loadingGitLabProjects}
            searchQuery={gitlabProjectSearch}
            setSearchQuery={setGitLabProjectSearch}
          />
          <SearchableMultiSelect
            label="Which versions/branches are these for?"
            helperText="Select the branches to monitor for releases and updates (usually 'main' or 'master')."
            searchPlaceholder="Search / filter branches..."
            items={getFilteredGitLabBranches()}
            selectedKeys={draft.config_json.release_branches || []}
            onChange={(branches) => updateConfig("release_branches", branches)}
            getOptionKey={(b) => b}
            getOptionLabel={(b) => b}
            getOptionSublabel={(b) => (draft.config_json.release_branches || []).includes(b) ? "Selected release branch" : "Git repository branch"}
            iconType="branch"
            loading={loadingGitLabBranches}
            searchQuery={gitlabBranchSearch}
            setSearchQuery={setGitLabBranchSearch}
          />
        </div>
      );
    }

    if (name === "finops") {
      return (
        <div className="config-columns settings-quick-grid" style={{ marginTop: "1rem" }}>
          <SearchableMultiSelect
            label="Which cloud providers are you using?"
            helperText="Select the cloud providers to monitor for cost optimization."
            searchPlaceholder="Search / filter providers..."
            items={getFilteredFinopsProviders()}
            selectedKeys={draft.config_json.providers || []}
            onChange={(providerKeys) => {
              updateConfig("providers", providerKeys);
              if (providerKeys.length > 0) loadFinopsProfiles(providerKeys[0]);
            }}
            getOptionKey={(p) => p.key}
            getOptionLabel={(p) => p.name}
            getOptionSublabel={(p) => (draft.config_json.providers || []).includes(p.key) ? "Active cloud provider" : "Supported provider"}
            iconType="project"
            loading={loadingFinopsProviders}
            searchQuery={finopsProviderSearch}
            setSearchQuery={setFinopsProviderSearch}
          />
          <SearchableMultiSelect
            label="Which billing profiles / cost reports?"
            helperText="Select the billing profiles or CURs (Cost and Usage Reports)."
            searchPlaceholder="Search / filter profiles..."
            items={getFilteredFinopsProfiles()}
            selectedKeys={draft.config_json.cost_file_paths || []}
            onChange={(profileIds) => updateConfig("cost_file_paths", profileIds)}
            getOptionKey={(p) => p.id}
            getOptionLabel={(p) => p.name}
            getOptionSublabel={(p) => `Billing Profile (ID: ${p.id})`}
            iconType="board"
            loading={loadingFinopsProfiles}
            searchQuery={finopsProfileSearch}
            setSearchQuery={setFinopsProfileSearch}
          />
        </div>
      );
    }
    return null;
  };

  return (
    <div className="onboarding-page">
      <style>{`
        .searchable-select {
          display: flex;
          flex-direction: column;
        }

        .searchable-select-input-wrapper {
          position: relative;
          display: flex;
          align-items: center;
          width: 100%;
        }

        .searchable-select-input {
          width: 100%;
          padding: 0.55rem 2rem 0.55rem 2.25rem !important;
          border-radius: 8px !important;
          border: 1px solid var(--border) !important;
          background: var(--surface) !important;
          color: var(--text) !important;
          font-size: 0.9rem !important;
          transition: all 0.2s ease;
        }

        .searchable-select-input:focus {
          border-color: var(--accent) !important;
          box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 15%, transparent) !important;
          outline: none;
        }

        .searchable-select-search-icon {
          position: absolute;
          left: 0.75rem;
          color: var(--muted);
          pointer-events: none;
          display: flex;
          align-items: center;
        }

        .searchable-select-clear-btn {
          position: absolute;
          right: 0.75rem;
          background: none;
          border: none;
          color: var(--muted);
          cursor: pointer;
          padding: 0.2rem;
          display: flex;
          align-items: center;
          border-radius: 999px;
        }

        .searchable-select-clear-btn:hover {
          background: var(--surface2);
          color: var(--text);
        }

        .searchable-select-list {
          max-height: 180px;
          overflow-y: auto;
          border: 1px solid var(--border);
          border-radius: 8px;
          margin-top: 0.45rem;
          background: var(--surface2);
          display: flex;
          flex-direction: column;
        }

        .searchable-select-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.6rem 0.8rem;
          border-bottom: 1px solid color-mix(in srgb, var(--border) 40%, transparent);
          cursor: pointer;
          transition: background 0.15s ease, border-left 0.15s ease;
          border-left: 3px solid transparent;
        }

        .searchable-select-item:last-child {
          border-bottom: none;
        }

        .searchable-select-item:hover {
          background: color-mix(in srgb, var(--accent) 5%, var(--surface));
        }

        .searchable-select-item--selected {
          background: color-mix(in srgb, var(--accent) 8%, var(--surface)) !important;
          border-left-color: var(--accent) !important;
        }

        .searchable-select-item-content {
          display: flex;
          align-items: center;
          gap: 0.7rem;
        }

        .searchable-select-item-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--muted);
        }

        .searchable-select-item--selected .searchable-select-item-icon {
          color: var(--accent);
        }

        .searchable-select-item-details {
          display: flex;
          flex-direction: column;
        }

        .searchable-select-item-title {
          font-size: 0.86rem;
          font-weight: 600;
          color: var(--text);
          line-height: 1.25;
        }

        .searchable-select-item-sublabel {
          font-size: 0.72rem;
          color: var(--muted);
          margin-top: 0.15rem;
          line-height: 1.15;
        }
      `}</style>

      <header className="gov-hub-header">
        <p className="gov-hub-eyebrow">Onboarding</p>
        <h1 className="gov-hub-title">Set up your workspace</h1>
        <p className="gov-hub-lead">Select your development branches and agile boards using configured settings.</p>
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
          <p className="field-hint" style={{ marginBottom: "1.25rem" }}>Select the active repository, release branch, and JIRA project/board for your workspace context.</p>
          
          {/* GitHub Form */}
          <div style={{ marginBottom: "1.5rem", paddingBottom: "1.5rem", borderBottom: "1px solid var(--border-color)" }}>
            <label className="onboarding-check" style={{ fontWeight: "bold", fontSize: "1.1rem", display: "flex", alignItems: "center", gap: "0.55rem" }}>
              <input
                type="checkbox"
                checked={connectors.github.enabled}
                onChange={(e) => handleToggle("github", e.target.checked)}
              />{" "}
              GitHub
            </label>
            {renderConnectorForm("github")}
          </div>

          {/* Jira Form */}
          <div style={{ marginBottom: "1.5rem", paddingBottom: "1.5rem", borderBottom: "1px solid var(--border-color)" }}>
            <label className="onboarding-check" style={{ fontWeight: "bold", fontSize: "1.1rem", display: "flex", alignItems: "center", gap: "0.55rem" }}>
              <input
                type="checkbox"
                checked={connectors.jira.enabled}
                onChange={(e) => handleToggle("jira", e.target.checked)}
              />{" "}
              Jira
            </label>
            {renderConnectorForm("jira")}
          </div>

          {/* GitLab Form */}
          <div style={{ marginBottom: "1.5rem", paddingBottom: "1.5rem", borderBottom: "1px solid var(--border-color)" }}>
            <label className="onboarding-check" style={{ fontWeight: "bold", fontSize: "1.1rem", display: "flex", alignItems: "center", gap: "0.55rem" }}>
              <input
                type="checkbox"
                checked={connectors.gitlab.enabled}
                onChange={(e) => handleToggle("gitlab", e.target.checked)}
              />{" "}
              GitLab
            </label>
            {renderConnectorForm("gitlab")}
          </div>

          {/* FinOps Form */}
          <div style={{ marginBottom: "1.5rem", paddingBottom: "1.5rem", borderBottom: "1px solid var(--border-color)" }}>
            <label className="onboarding-check" style={{ fontWeight: "bold", fontSize: "1.1rem", display: "flex", alignItems: "center", gap: "0.55rem" }}>
              <input
                type="checkbox"
                checked={connectors.finops.enabled}
                onChange={(e) => handleToggle("finops", e.target.checked)}
              />{" "}
              FinOps (Cloud Cost Management)
            </label>
            {renderConnectorForm("finops")}
          </div>
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
          <h2>Connection Summary</h2>
          <p className="field-hint" style={{ marginBottom: "1.5rem" }}>
            Review the connections established for your workspace.
          </p>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {connectors.github.enabled && (
              <div style={{ background: "var(--bg-subtle)", padding: "1.25rem", borderRadius: "6px", border: "1px solid var(--border-color)" }}>
                <h4 style={{ margin: 0, color: "var(--primary-color)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span>GitHub Connected</span>
                  <span style={{ color: "var(--success-color)", fontSize: "0.9rem" }}>✓</span>
                </h4>
                <ul style={{ marginTop: "0.75rem", paddingLeft: "1.25rem", margin: "0.75rem 0 0 0", wordBreak: "break-all" }}>
                  <li style={{ marginBottom: "0.5rem" }}>
                    <strong>Repositories:</strong>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginTop: "0.4rem" }}>
                      {(connectors.github.config_json.repos || []).map((r: string) => (
                        <span key={r} style={{ background: "var(--bg-muted)", padding: "0.2rem 0.5rem", borderRadius: "12px", fontSize: "0.85rem", border: "1px solid var(--border-color)" }}>{r}</span>
                      ))}
                    </div>
                  </li>
                  <li>
                    <strong>Branches:</strong>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginTop: "0.4rem" }}>
                      {(connectors.github.config_json.release_branches || ["main"]).map((b: string) => (
                        <span key={b} style={{ background: "var(--bg-muted)", padding: "0.2rem 0.5rem", borderRadius: "12px", fontSize: "0.85rem", border: "1px solid var(--border-color)" }}>{b}</span>
                      ))}
                    </div>
                  </li>
                </ul>
              </div>
            )}

            {connectors.jira.enabled && (
              <div style={{ background: "var(--bg-subtle)", padding: "1.25rem", borderRadius: "6px", border: "1px solid var(--border-color)" }}>
                <h4 style={{ margin: 0, color: "var(--primary-color)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span>Jira Connected</span>
                  <span style={{ color: "var(--success-color)", fontSize: "0.9rem" }}>✓</span>
                </h4>
                <ul style={{ marginTop: "0.75rem", paddingLeft: "1.25rem", margin: "0.75rem 0 0 0", wordBreak: "break-all" }}>
                  <li style={{ marginBottom: "0.5rem" }}>
                    <strong>Projects:</strong>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginTop: "0.4rem" }}>
                      {(connectors.jira.config_json.projects || []).map((p: string) => (
                        <span key={p} style={{ background: "var(--bg-muted)", padding: "0.2rem 0.5rem", borderRadius: "12px", fontSize: "0.85rem", border: "1px solid var(--border-color)" }}>{p}</span>
                      ))}
                    </div>
                  </li>
                  <li>
                    <strong>Boards:</strong>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginTop: "0.4rem" }}>
                      {(connectors.jira.config_json.board_ids || []).map((b: string) => (
                        <span key={b} style={{ background: "var(--bg-muted)", padding: "0.2rem 0.5rem", borderRadius: "12px", fontSize: "0.85rem", border: "1px solid var(--border-color)" }}>{b}</span>
                      ))}
                    </div>
                  </li>
                </ul>
              </div>
            )}

            {connectors.gitlab.enabled && (
              <div style={{ background: "var(--bg-subtle)", padding: "1.25rem", borderRadius: "6px", border: "1px solid var(--border-color)" }}>
                <h4 style={{ margin: 0, color: "var(--primary-color)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span>GitLab Connected</span>
                  <span style={{ color: "var(--success-color)", fontSize: "0.9rem" }}>✓</span>
                </h4>
                <ul style={{ marginTop: "0.75rem", paddingLeft: "1.25rem", margin: "0.75rem 0 0 0", wordBreak: "break-all" }}>
                  <li style={{ marginBottom: "0.5rem" }}>
                    <strong>Projects:</strong>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginTop: "0.4rem" }}>
                      {(connectors.gitlab.config_json.project_ids || []).map((p: string) => (
                        <span key={p} style={{ background: "var(--bg-muted)", padding: "0.2rem 0.5rem", borderRadius: "12px", fontSize: "0.85rem", border: "1px solid var(--border-color)" }}>{p}</span>
                      ))}
                    </div>
                  </li>
                  <li>
                    <strong>Branches:</strong>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginTop: "0.4rem" }}>
                      {(connectors.gitlab.config_json.release_branches || ["main"]).map((b: string) => (
                        <span key={b} style={{ background: "var(--bg-muted)", padding: "0.2rem 0.5rem", borderRadius: "12px", fontSize: "0.85rem", border: "1px solid var(--border-color)" }}>{b}</span>
                      ))}
                    </div>
                  </li>
                </ul>
              </div>
            )}

            {connectors.finops.enabled && (
              <div style={{ background: "var(--bg-subtle)", padding: "1.25rem", borderRadius: "6px", border: "1px solid var(--border-color)" }}>
                <h4 style={{ margin: 0, color: "var(--primary-color)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span>FinOps Connected</span>
                  <span style={{ color: "var(--success-color)", fontSize: "0.9rem" }}>✓</span>
                </h4>
                <ul style={{ marginTop: "0.75rem", paddingLeft: "1.25rem", margin: "0.75rem 0 0 0", wordBreak: "break-all" }}>
                  <li style={{ marginBottom: "0.5rem" }}>
                    <strong>Cloud Providers:</strong>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginTop: "0.4rem" }}>
                      {(connectors.finops.config_json.providers || ["aws"]).map((p: string) => (
                        <span key={p} style={{ background: "var(--bg-muted)", padding: "0.2rem 0.5rem", borderRadius: "12px", fontSize: "0.85rem", border: "1px solid var(--border-color)" }}>{p}</span>
                      ))}
                    </div>
                  </li>
                  <li>
                    <strong>Billing Profiles:</strong>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginTop: "0.4rem" }}>
                      {(connectors.finops.config_json.cost_file_paths || []).map((c: string) => (
                        <span key={c} style={{ background: "var(--bg-muted)", padding: "0.2rem 0.5rem", borderRadius: "12px", fontSize: "0.85rem", border: "1px solid var(--border-color)" }}>{c}</span>
                      ))}
                    </div>
                  </li>
                </ul>
              </div>
            )}

            {!connectors.github.enabled && !connectors.jira.enabled && !connectors.gitlab.enabled && !connectors.finops.enabled && (
              <div style={{ background: "var(--bg-subtle)", padding: "1.25rem", borderRadius: "6px", border: "1px solid var(--border-color)", textAlign: "center" }}>
                <p style={{ margin: 0, color: "var(--text-muted)" }}>No connections established.</p>
              </div>
            )}
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
