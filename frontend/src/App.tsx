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
import { loadToken, saveToken } from "./authStorage";
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
import { WorkspaceSettingsPage } from "./pages/WorkspaceSettingsPage";
import { WorkspaceLeadsPage } from "./pages/WorkspaceLeadsPage";
import { WorkspaceTenantsPage } from "./pages/WorkspaceTenantsPage";
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
  const [token, setToken] = useState<string | null>(() => loadToken());
  const [user, setUser] = useState<UserPublic | null>(null);
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
    if (!token) {
      setUser(null);
      return;
    }
    fetchMe(token)
      .then(setUser)
      .catch(() => {
        saveToken(null);
        setToken(null);
      });
  }, [token]);

  useEffect(() => {
    fetchPromptLibrary()
      .then(setLibrary)
      .catch(() => setLibrary({ prompts: [] }));
  }, []);

  useEffect(() => {
    if (!token || !user?.is_superadmin) {
      setTenants(null);
      return;
    }
    fetchTenants(token)
      .then(setTenants)
      .catch(() => setTenants([]));
  }, [token, user?.is_superadmin]);

  useEffect(() => {
    if (!token) {
      setApiCompatibilityWarning(null);
      return;
    }
    fetchDashboardSummary(token)
      .then(() => setApiCompatibilityWarning(null))
      .catch(() =>
        setApiCompatibilityWarning(
          "Backend API appears outdated or mismatched. Restart backend on port 8000 from this repo."
        )
      );
  }, [token]);

  const handleAuthed = (data: LoginResponse) => {
    saveToken(data.access_token);
    setToken(data.access_token);
    setUser(data.user);
  };

  const handleLogout = () => {
    saveToken(null);
    setToken(null);
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
    if (!token || !newTenantName.trim() || !newTenantSlug.trim()) return;
    setError(null);
    setLoading(true);
    try {
      await createTenant(token, { name: newTenantName.trim(), slug: newTenantSlug.trim() });
      setNewTenantName("");
      setNewTenantSlug("");
      const list = await fetchTenants(token);
      setTenants(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create tenant");
    } finally {
      setLoading(false);
    }
  };

  const handleRun = async () => {
    if (!token || !prompt.trim()) return;
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const data = await runGovernance(token, prompt.trim(), promptId, user?.tenant_slug);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setLoading(false);
    }
  };

  const handleBatch = async () => {
    if (!token) return;
    setError(null);
    setLoading(true);
    setBatchResult(null);
    try {
      const data = await runGovernanceBatch(token, user?.tenant_slug);
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
          token && user ? (
            <Navigate to="/app" replace />
          ) : token && !user ? (
            <div className="marketing auth-page">
              <div className="auth-panel">
                <p style={{ color: "var(--muted)" }}>Restoring session…</p>
              </div>
            </div>
          ) : (
            <LoginPage onAuthed={handleAuthed} signupEnabled={signupEnabled} />
          )
        }
      />
      <Route
        path="/signup"
        element={
          token && user ? (
            <Navigate to="/app" replace />
          ) : token && !user ? (
            <div className="marketing auth-page">
              <div className="auth-panel">
                <p style={{ color: "var(--muted)" }}>Restoring session…</p>
              </div>
            </div>
          ) : (
            <SignupPage onAuthed={handleAuthed} />
          )
        }
      />
      <Route
        path="/app"
        element={
          !token ? (
            <Navigate to="/login" replace />
          ) : !user ? (
            <div className="app" style={{ padding: "2rem" }}>
              <p style={{ color: "var(--muted)" }}>Loading workspace…</p>
            </div>
          ) : (
            <WorkspaceShell user={user} onLogout={handleLogout} theme={theme} onToggleTheme={handleToggleTheme} />
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
        <Route path="dashboard" element={<WorkspaceHomePage token={token} user={user as UserPublic} />} />
        <Route path="runs" element={<WorkspaceRunsPage token={token} tenantSlug={user?.tenant_slug} />} />
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
        <Route path="evidence" element={<WorkspaceEvidencePage token={token} />} />
        <Route
          path="cases"
          element={
            <WorkspaceCasesPage
              token={token}
              tenantSlug={user?.tenant_slug}
              canManage={Boolean(user?.is_superadmin || user?.is_admin)}
            />
          }
        />
        <Route path="alerts" element={<WorkspaceAlertsPage token={token} />} />
        <Route
          path="integrations"
          element={
            <WorkspaceIntegrationsPage
              token={token}
              tenantSlug={user?.tenant_slug}
              canManage={Boolean(user?.is_superadmin || user?.is_admin)}
            />
          }
        />
        <Route
          path="portfolio"
          element={<WorkspacePortfolioPage token={token} canManage={Boolean(user?.is_superadmin || user?.is_admin)} />}
        />
        <Route path="reports" element={<WorkspaceReportsPage token={token} />} />
        <Route
          path="settings"
          element={<WorkspaceSettingsPage token={token} user={user as UserPublic} tenants={tenants} initialTab="general" />}
        />
        <Route
          path="ai-config"
          element={<WorkspaceSettingsPage token={token} user={user as UserPublic} tenants={tenants} initialTab="ai" />}
        />
        <Route path="leads" element={<WorkspaceLeadsPage token={token} />} />
        <Route path="tenants" element={user?.is_superadmin ? <WorkspaceTenantsPage token={token} /> : <Navigate to="/app/dashboard" replace />} />
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
