import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import {
  createTenant,
  fetchDashboardSummary,
  fetchMe,
  fetchPromptLibrary,
  fetchTenants,
  fetchSignupStatus,
  runGovernance,
  runGovernanceBatch,
  type GovernanceRunResult,
  type LoginResponse,
  type PromptLibrary,
  type TenantRow,
  type UserPublic,
} from "./api";
import { WorkspaceShell } from "./components/WorkspaceShell";
import { GovernanceView } from "./GovernanceView";
import { LoginPage } from "./pages/LoginPage";
import { WorkspaceAlertsPage } from "./pages/WorkspaceAlertsPage";
import { WorkspaceCasesPage } from "./pages/WorkspaceCasesPage";
import { CapabilitiesPage } from "./pages/CapabilitiesPage";
import { EnterprisePage } from "./pages/EnterprisePage";
import { HowItWorksPage } from "./pages/HowItWorksPage";
import { MarketingPage } from "./pages/MarketingPage";
import { PlatformPage } from "./pages/PlatformPage";
import { SignupPage } from "./pages/SignupPage";
import { WorkspaceEvidencePage } from "./pages/WorkspaceEvidencePage";
import { WorkspaceHomePage } from "./pages/WorkspaceHomePage";
import { WorkspaceIntegrationsPage } from "./pages/WorkspaceIntegrationsPage";
import { WorkspacePortfolioPage } from "./pages/WorkspacePortfolioPage";
import { RequestAccessPage } from "./pages/RequestAccessPage";
import { WorkspaceReportsPage } from "./pages/WorkspaceReportsPage";
import { WorkspaceRunsPage } from "./pages/WorkspaceRunsPage";
import { WorkspaceBriefPage } from "./pages/WorkspaceBriefPage";
import { WorkspaceSettingsPage } from "./pages/WorkspaceSettingsPage";
import { WorkspaceToolRegistryPage } from "./pages/WorkspaceToolRegistryPage";
import { WorkspaceLeadsPage } from "./pages/WorkspaceLeadsPage";
import { WorkspaceTenantsPage } from "./pages/WorkspaceTenantsPage";
import { OnboardingWizardPage } from "./pages/OnboardingWizardPage";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

function AppRoutes() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = localStorage.getItem("workspace-theme");
    return saved === "dark" ? "dark" : "light";
  });
  const [user, setUser] = useState<UserPublic | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [tenants, setTenants] = useState<TenantRow[] | null>(null);
  const [newTenantName, setNewTenantName] = useState("");
  const [newTenantSlug, setNewTenantSlug] = useState("");
  const [prompt, setPrompt] = useState("");
  const [promptId, setPromptId] = useState<string | null>(null);
  const [library, setLibrary] = useState<PromptLibrary | null>(null);
  const [result, setResult] = useState<GovernanceRunResult | null>(null);
  const [batchResult, setBatchResult] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [signupEnabled, setSignupEnabled] = useState<boolean | null>(null);
  const [apiCompatibilityWarning, setApiCompatibilityWarning] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("workspace-theme", theme);
  }, [theme]);

  useEffect(() => {
    fetchSignupStatus()
      .then((s) => setSignupEnabled(s.tenant_signup_enabled))
      .catch(() => setSignupEnabled(false));
  }, []);

  useEffect(() => {
    fetchMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setAuthChecked(true));
  }, []);

  useEffect(() => {
    fetchPromptLibrary()
      .then(setLibrary)
      .catch(() => setLibrary({ prompts: [] }));
  }, []);

  useEffect(() => {
    if (!user?.is_superadmin) {
      setTenants(null);
      return;
    }
    fetchTenants()
      .then(setTenants)
      .catch(() => setTenants([]));
  }, [user?.is_superadmin]);

  useEffect(() => {
    if (!user) {
      setApiCompatibilityWarning(null);
      return;
    }
    fetchDashboardSummary()
      .then(() => setApiCompatibilityWarning(null))
      .catch(() =>
        setApiCompatibilityWarning(
          "Backend API appears outdated or mismatched. Restart backend on port 8000 from this repo."
        )
      );
  }, [user]);

  const handleAuthed = (data: LoginResponse) => {
    setUser(data.user);
  };

  const handleLogout = async () => {
    try {
      await fetch("/api/v1/auth/logout", { method: "POST", credentials: "include" });
    } catch { }
    setUser(null);
    setTenants(null);
    setResult(null);
    setBatchResult(null);
  };

  const handleToggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  const handleCreateTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    if ( !newTenantName.trim() || !newTenantSlug.trim()) return;
    setError(null);
    setLoading(true);
    try {
      await createTenant({ name: newTenantName.trim(), slug: newTenantSlug.trim() });
      setNewTenantName("");
      setNewTenantSlug("");
      const list = await fetchTenants();
      setTenants(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create tenant");
    } finally {
      setLoading(false);
    }
  };

  const handleRun = async () => {
    if ( !prompt.trim()) return;
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const data = await runGovernance(prompt.trim(), promptId, user?.tenant_slug);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setLoading(false);
    }
  };

  const handleBatch = async () => {
    
    setError(null);
    setLoading(true);
    setBatchResult(null);
    try {
      const data = await runGovernanceBatch(user?.tenant_slug);
      setBatchResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Batch failed");
    } finally {
      setLoading(false);
    }
  };

  const applyLibraryPrompt = (id: string) => {
    const p = library?.prompts.find((x) => x.id === id);
    if (p) {
      setPrompt(p.text);
      setPromptId(p.id);
    }
  };

  if (!authChecked) return <div className="app">Loading...</div>;

  return (
    <Routes>
      <Route path="/" element={<MarketingPage />} />
      <Route path="/platform" element={<PlatformPage />} />
      <Route path="/capabilities" element={<CapabilitiesPage />} />
      <Route path="/how-it-works" element={<HowItWorksPage />} />
      <Route path="/enterprise" element={<EnterprisePage />} />
      <Route path="/request-access" element={<RequestAccessPage />} />
      <Route
        path="/login"
        element={
          user ? (
            <Navigate to="/app" replace />
          ) : (
            <LoginPage onAuthed={handleAuthed} signupEnabled={signupEnabled} />
          )
        }
      />
      <Route
        path="/signup"
        element={
          user ? (
            <Navigate to="/app" replace />
          ) : (
            <SignupPage onAuthed={handleAuthed} />
          )
        }
      />
      <Route
        path="/app"
        element={
          user ? (
            <WorkspaceShell user={user} onLogout={handleLogout} theme={theme} onToggleTheme={handleToggleTheme} />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      >
        {apiCompatibilityWarning ? (
          <Route
            path="*"
            element={
              <div className="app">
                <div className="alert alert-error">{apiCompatibilityWarning}</div>
              </div>
            }
          />
        ) : null}
        <Route index element={<Navigate to="/app/dashboard" replace />} />
        <Route path="home" element={<Navigate to="/app/dashboard" replace />} />
        <Route path="dashboard" element={<WorkspaceHomePage user={user as UserPublic} />} />
        <Route path="runs" element={<WorkspaceRunsPage tenantSlug={user?.tenant_slug} />} />
        <Route path="brief" element={<WorkspaceBriefPage />} />
        <Route
          path="overview"
          element={
            <GovernanceView
              user={user as UserPublic}
              error={error}
              tenants={tenants}
              newTenantName={newTenantName}
              setNewTenantName={setNewTenantName}
              newTenantSlug={newTenantSlug}
              setNewTenantSlug={setNewTenantSlug}
              onCreateTenant={handleCreateTenant}
              prompt={prompt}
              setPrompt={setPrompt}
              promptId={promptId}
              setPromptId={setPromptId}
              library={library}
              applyLibraryPrompt={applyLibraryPrompt}
              onRunGovernance={handleRun}
              onBatch={handleBatch}
              loading={loading}
              result={result}
              batchResult={batchResult}
            />
          }
        />
        <Route path="evidence" element={<WorkspaceEvidencePage />} />
        <Route
          path="cases"
          element={
            <WorkspaceCasesPage
              
              tenantSlug={user?.tenant_slug}
              canManage={Boolean(user?.is_superadmin || user?.is_admin)}
            />
          }
        />
        <Route path="alerts" element={<WorkspaceAlertsPage />} />
        <Route
          path="integrations"
          element={
            <WorkspaceIntegrationsPage
              
              tenantSlug={user?.tenant_slug}
              canManage={Boolean(user?.is_superadmin || user?.is_admin)}
            />
          }
        />
        <Route
          path="portfolio"
          element={<WorkspacePortfolioPage canManage={Boolean(user?.is_superadmin || user?.is_admin)} />}
        />
        <Route path="reports" element={<WorkspaceReportsPage />} />
        <Route
          path="settings"
          element={<WorkspaceSettingsPage user={user as UserPublic} tenants={tenants} initialTab="general" />}
        />
        <Route
          path="ai-config"
          element={<WorkspaceSettingsPage user={user as UserPublic} tenants={tenants} initialTab="ai" />}
        />
        <Route path="tool-registry" element={<WorkspaceToolRegistryPage />} />
        <Route path="onboarding" element={<OnboardingWizardPage />} />
        <Route path="leads" element={<WorkspaceLeadsPage />} />
        <Route path="tenants" element={user?.is_superadmin ? <WorkspaceTenantsPage /> : <Navigate to="/app/dashboard" replace />} />
      </Route>
      <Route
        path="*"
        element={
          <div className="app">
            <div className="card">
              <h2>Page not found</h2>
              <p style={{ color: "var(--muted)", marginTop: 0 }}>The requested route does not exist.</p>
            </div>
          </div>
        }
      />
    </Routes>
  );
}
