import type { UserPublic } from "../api";

type WorkspaceHomePageProps = {
  user: UserPublic;
};

export function WorkspaceHomePage({ user }: WorkspaceHomePageProps) {
  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <h1>Home</h1>
          <span>Governance copilot dashboard</span>
        </div>
      </header>
      <div className="metrics">
        <div className="metric">
          <div className="label">Role</div>
          <div className="value">{user.is_superadmin ? "Superadmin" : user.is_admin ? "Tenant admin" : "User"}</div>
        </div>
        <div className="metric">
          <div className="label">Tenant</div>
          <div className="value mono">{user.tenant_slug ?? "platform"}</div>
        </div>
        <div className="metric">
          <div className="label">Next step</div>
          <div className="value" style={{ fontSize: "0.95rem" }}>
            Open Runs to start and track governance jobs.
          </div>
        </div>
      </div>
    </div>
  );
}
