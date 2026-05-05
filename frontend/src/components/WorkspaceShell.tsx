import { NavLink, Outlet } from "react-router-dom";
import type { UserPublic } from "../api";

type WorkspaceShellProps = {
  user: UserPublic;
  onLogout: () => void;
};

export function WorkspaceShell({ user, onLogout }: WorkspaceShellProps) {
  return (
    <div className="workspace">
      <aside className="workspace-sidebar">
        <div className="workspace-logo">
          <h2>AgileOps</h2>
          <span>
            {user.is_superadmin ? "superadmin" : user.tenant_slug ? `tenant: ${user.tenant_slug}` : "workspace"}
          </span>
        </div>
        <nav className="workspace-nav">
          <NavLink to="/app/home">Home</NavLink>
          <NavLink to="/app/runs">Runs</NavLink>
          <NavLink to="/app/evidence">Evidence</NavLink>
          <NavLink to="/app/cases">Cases</NavLink>
          <NavLink to="/app/alerts">Alerts</NavLink>
          <NavLink to="/app/reports">Reports</NavLink>
          <NavLink to="/app/overview">Overview</NavLink>
          <NavLink to="/app/settings">Settings</NavLink>
          <NavLink to="/app/ai-config">AI Config</NavLink>
        </nav>
        <button type="button" className="btn btn-ghost" onClick={onLogout}>
          Sign out
        </button>
      </aside>
      <main className="workspace-main">
        <Outlet />
      </main>
    </div>
  );
}
