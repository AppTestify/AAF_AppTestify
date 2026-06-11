import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { UserPublic } from "../api";

type WorkspaceTopBarProps = {
  user: UserPublic;
};

export function WorkspaceTopBar({ user }: WorkspaceTopBarProps) {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const roleLabel = user.is_superadmin ? "Superadmin" : user.is_admin ? "Admin" : "Reviewer";
  const initials = user.email.slice(0, 2).toUpperCase();

  const onSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    navigate(`/app/runs?query=${encodeURIComponent(q)}`);
  };

  return (
    <header className="workspace-topbar">
      <form className="workspace-topbar-search" onSubmit={onSearch}>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search decisions, evidence, agents…"
          aria-label="Search workspace"
        />
      </form>
      <div className="workspace-topbar-actions">
        <Link to="/app/alerts" className="workspace-topbar-bell" aria-label="Notifications">
          🔔
        </Link>
        <div className="workspace-topbar-user">
          <span className="workspace-topbar-avatar" aria-hidden="true">
            {initials}
          </span>
          <div className="workspace-topbar-user-text">
            <strong>{user.email.split("@")[0]}</strong>
            <span>{roleLabel}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
