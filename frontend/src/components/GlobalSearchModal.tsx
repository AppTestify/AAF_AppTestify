import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { globalSearch, type GlobalSearchResult } from "../api";

const RECENT_KEY = "casantris.recentSearches";

type GlobalSearchModalProps = {
  open: boolean;
  onClose: () => void;
};

export function GlobalSearchModal({ open, onClose }: GlobalSearchModalProps) {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<GlobalSearchResult | null>(null);
  const [recent, setRecent] = useState<string[]>([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(RECENT_KEY);
      setRecent(raw ? (JSON.parse(raw) as string[]) : []);
    } catch {
      setRecent([]);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const runSearch = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    const data = await globalSearch(trimmed);
    setResult(data);
    const next = [trimmed, ...recent.filter((r) => r !== trimmed)].slice(0, 8);
    setRecent(next);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  };

  if (!open) return null;

  return (
    <div className="gov-search-overlay" role="dialog" aria-modal="true" aria-label="Global search">
      <div className="gov-search-modal">
        <input
          autoFocus
          type="search"
          className="gov-search-input"
          placeholder="Search decisions, evidence, cases…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void runSearch(query);
          }}
        />
        <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
          Esc
        </button>
        {recent.length ? (
          <div className="gov-search-recent">
            {recent.map((r) => (
              <button key={r} type="button" className="gov-search-chip" onClick={() => void runSearch(r)}>
                {r}
              </button>
            ))}
          </div>
        ) : null}
        {result ? (
          <div className="gov-search-groups">
            {(["runs", "cases", "evidence"] as const).map((group) => (
              <section key={group}>
                <h4>{group}</h4>
                <ul>
                  {(result.groups[group] ?? []).map((item) => (
                    <li key={`${group}-${item.id}`}>
                      {group === "runs" ? (
                        <Link to={`/app/runs?run=${item.id}`} onClick={onClose}>
                          {(item as { prompt?: string }).prompt ?? `#${item.id}`}
                        </Link>
                      ) : (
                        <span>{JSON.stringify(item)}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
