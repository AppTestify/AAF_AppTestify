import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { UserPublic } from "../api";
import { GlobalSearchModal } from "./GlobalSearchModal";

type WorkspaceTopBarProps = {
  user: UserPublic;
};

export function WorkspaceTopBar({ user }: WorkspaceTopBarProps) {
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const navigate = useNavigate();

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
