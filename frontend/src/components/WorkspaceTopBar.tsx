import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { UserPublic } from "../api";
import { useDashboardSummary } from "../hooks/useDashboardSummary";
import { GlobalSearchModal } from "./GlobalSearchModal";

type WorkspaceTopBarProps = {
  user: UserPublic;
};

export function WorkspaceTopBar({ user }: WorkspaceTopBarProps) {
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const navigate = useNavigate();
  const { summary } = useDashboardSummary();

  const runningCount = useMemo(
    () => (summary?.recent_runs ?? []).filter((r) => r.status === "running" || r.status === "queued").length,
    [summary]
  );
  const alertCount = summary?.alerts_24h ?? 0;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

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
      <GlobalSearchModal open={searchOpen} onClose={() => setSearchOpen(false)} />
      <form className="workspace-topbar-search" onSubmit={onSearch}>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search decisions, evidence, agents… (⌘K)"
          aria-label="Search workspace"
          onFocus={() => setSearchOpen(true)}
        />
      </form>
      <div className="workspace-topbar-actions">
        {runningCount > 0 ? (
          <span className="workspace-topbar-running" title="Governance runs in progress">
            <span className="status-pulse-dot" aria-hidden="true" />
            {runningCount} running
          </span>
        ) : null}
        <button type="button" className="btn btn-ghost btn-sm workspace-topbar-search-btn" onClick={() => setSearchOpen(true)}>
          Search
        </button>
        <Link to="/app/alerts" className="workspace-topbar-bell" aria-label="Notifications">
          🔔
          {alertCount > 0 ? <span className="workspace-nav-badge workspace-topbar-alert-badge">{alertCount}</span> : null}
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
