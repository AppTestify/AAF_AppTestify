import { NavLink, Outlet } from "react-router-dom";
import type { UserPublic } from "../api";

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
            <span>
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
          <p className="workspace-nav-group">Operations</p>
          <NavLink to="/app/dashboard">Dashboard</NavLink>
          <NavLink to="/app/overview">Overview</NavLink>
          <NavLink to="/app/runs">Runs</NavLink>
          <NavLink to="/app/evidence">Evidence</NavLink>
          <NavLink to="/app/cases">Cases</NavLink>
          <NavLink to="/app/alerts">Alerts</NavLink>
          <p className="workspace-nav-group">Control plane</p>
          <NavLink to="/app/integrations">Integrations</NavLink>
          <NavLink to="/app/portfolio">Portfolio</NavLink>
          <NavLink to="/app/reports">Reports</NavLink>
          <NavLink to="/app/settings">Settings</NavLink>
          <NavLink to="/app/ai-config">AI Config</NavLink>
          {user.is_superadmin ? <NavLink to="/app/tenants">Tenants</NavLink> : null}
          {user.is_superadmin ? <NavLink to="/app/leads">Leads</NavLink> : null}
        </nav>
        <div className="workspace-sidebar-footer">
          <button type="button" className="btn btn-ghost workspace-signout" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="workspace-main">
        <Outlet />
      </main>
    </div>
  );
}
