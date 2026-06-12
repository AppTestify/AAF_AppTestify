import { NavLink, Outlet } from "react-router-dom";
import type { UserPublic } from "../api";
import { GovernanceConfidenceWidget } from "./GovernanceConfidenceWidget";
import { WorkspaceTopBar } from "./WorkspaceTopBar";

type WorkspaceShellProps = {
  user: UserPublic;
  onLogout: () => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
};

export function WorkspaceShell({ user, onLogout, theme, onToggleTheme }: WorkspaceShellProps) {
  return (
    <div className="workspace">
      <aside className="workspace-sidebar">
        <div className="workspace-logo">
          <div className="workspace-logo-mark" aria-hidden="true" />
          <div>
            <h2>Casantris</h2>
            <span className="workspace-logo-suite">Governance Suite</span>
            <span className="workspace-logo-tenant">
              {user.is_superadmin ? "enterprise core" : user.tenant_slug ? `tenant: ${user.tenant_slug}` : "workspace"}
            </span>
          </div>
        </div>
        <button
          type="button"
          className="workspace-theme-toggle"
          onClick={onToggleTheme}
          aria-label={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
          title={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
        >
          <span className="theme-icon" aria-hidden="true">
            {theme === "light" ? "🌙" : "☀️"}
          </span>
          <span>{theme === "light" ? "Dark mode" : "Light mode"}</span>
        </button>
        <nav className="workspace-nav">
          <p className="workspace-nav-group">Workspace</p>
          <NavLink to="/app/dashboard">Command Center</NavLink>
          <NavLink to="/app/overview">Ask Casantris AI</NavLink>
          <NavLink to="/app/evidence">Evidence Hub</NavLink>
          <NavLink to="/app/runs">Agentic Governance</NavLink>
          <NavLink to="/app/cases">Decision & Audit</NavLink>
          <NavLink to="/app/brief">Executive Brief</NavLink>
          <p className="workspace-nav-group">Control plane</p>
          <NavLink to="/app/alerts">Alerts</NavLink>
          <NavLink to="/app/integrations">Integrations</NavLink>
          <NavLink to="/app/portfolio">Portfolio</NavLink>
          <NavLink to="/app/reports">Reports</NavLink>
          <NavLink to="/app/settings">Settings</NavLink>
          <NavLink to="/app/ai-config">AI Config</NavLink>
          <NavLink to="/app/tool-registry">Tool Registry</NavLink>
          {user.is_superadmin ? <NavLink to="/app/tenants">Tenants</NavLink> : null}
          {user.is_superadmin ? <NavLink to="/app/leads">Leads</NavLink> : null}
        </nav>
        <GovernanceConfidenceWidget />
        <div className="workspace-sidebar-footer">
          <button type="button" className="btn btn-ghost workspace-signout" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </aside>
      <div className="workspace-content">
        <WorkspaceTopBar user={user} />
        <main className="workspace-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
