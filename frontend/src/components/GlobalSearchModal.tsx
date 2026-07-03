import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { globalSearch, type GlobalSearchResult } from "../api";

const RECENT_KEY = "casantris.recentSearches";

type SearchHit = {
  group: "runs" | "cases" | "evidence";
  id: number;
  title: string;
  subtitle: string;
  path: string;
  status?: string;
};

type GlobalSearchModalProps = {
  open: boolean;
  onClose: () => void;
};

function buildHits(result: GlobalSearchResult): SearchHit[] {
  const hits: SearchHit[] = [];
  for (const run of result.groups.runs ?? []) {
    hits.push({
      group: "runs",
      id: run.id,
      title: run.prompt ?? `Run #${run.id}`,
      subtitle: `ID #${run.id}`,
      path: `/app/runs?run_id=${run.id}`,
      status: run.status,
    });
  }
  for (const c of result.groups.cases ?? []) {
    hits.push({
      group: "cases",
      id: c.id,
      title: c.title ?? `Case #${c.id}`,
      subtitle: `case #${c.id}`,
      path: `/app/cases?case_id=${c.id}`,
      status: c.status,
    });
  }
  for (const ev of result.groups.evidence ?? []) {
    const runId = ev.run_id ?? ev.id;
    const connector = ev.connector ?? "Evidence";
    hits.push({
      group: "evidence",
      id: ev.id,
      title: `${connector} (run #${runId})`,
      subtitle: `evidence #${ev.id}`,
      path: `/app/evidence?run_id=${runId}`,
    });
  }
  return hits;
}

export function GlobalSearchModal({ open, onClose }: GlobalSearchModalProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<GlobalSearchResult | null>(null);
  const [recent, setRecent] = useState<string[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  const hits = useMemo(() => (result ? buildHits(result) : []), [result]);

  const groupedHits = useMemo(() => {
    const groups: Record<"runs" | "cases" | "evidence", SearchHit[]> = {
      runs: [],
      cases: [],
      evidence: [],
    };
    for (const h of hits) groups[h.group].push(h);
    return groups;
  }, [hits]);

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
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (!hits.length) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, hits.length - 1));
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
      }
      if (e.key === "Enter") {
        e.preventDefault();
        const hit = hits[activeIndex];
        if (hit) {
          navigate(hit.path);
          onClose();
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose, hits, activeIndex, navigate]);

  useEffect(() => {
    setActiveIndex(0);
  }, [result]);

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

  let flatIndex = -1;

  return (
    <div className="gov-search-overlay" role="dialog" aria-modal="true" aria-label="Global search" onClick={onClose}>
      <div className="gov-search-modal" onClick={(e) => e.stopPropagation()}>
        <input
          autoFocus
          type="search"
          className="gov-search-input"
          placeholder="Search decisions, evidence, cases…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !hits.length) void runSearch(query);
          }}
        />
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
          <div className="gov-search-groups" ref={listRef}>
            {(["runs", "cases", "evidence"] as const).map((group) => {
              const items = groupedHits[group];
              if (!items.length) return null;
              return (
                <section key={group} className="gov-search-section">
                  <h4>{group.toUpperCase()}</h4>
                  <ul>
                    {items.map((hit) => {
                      flatIndex += 1;
                      const idx = flatIndex;
                      const isActive = idx === activeIndex;
                      return (
                        <li key={`${group}-${hit.id}`}>
                          <Link
                            to={hit.path}
                            className={`gov-search-hit ${isActive ? "gov-search-hit--active" : ""}`}
                            onClick={onClose}
                            onMouseEnter={() => setActiveIndex(idx)}
                          >
                            <div className="gov-search-hit-main">
                              <span className="gov-search-hit-title">{hit.title}</span>
                              <span className="gov-search-hit-meta">
                                {hit.subtitle}
                                {hit.status ? (
                                  <>
                                    {" "}
                                    · <span className={`status-chip status-chip--inline ${hit.status}`}>{hit.status}</span>
                                  </>
                                ) : null}
                              </span>
                            </div>
                            <code className="gov-search-hit-path">{hit.path}</code>
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                </section>
              );
            })}
            {hits.length === 0 ? <p className="gov-search-empty">No results for &ldquo;{result.query}&rdquo;</p> : null}
          </div>
        ) : null}
        <footer className="gov-search-footer">
          <span>↑↓ navigate</span>
          <span>↵ open</span>
          <span>⌘K toggle</span>
        </footer>
      </div>
    </div>
  );
}
