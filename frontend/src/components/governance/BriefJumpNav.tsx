type BriefJumpNavProps = {
  activeId: string;
  onSelect: (id: string) => void;
};

const SECTIONS = [
  { id: "executive", label: "Executive summary" },
  { id: "guardrails", label: "Guardrail posture" },
  { id: "reasoning", label: "Agent reasoning" },
  { id: "audit", label: "Audit trail" },
  { id: "cost", label: "LLM cost" },
] as const;

export function BriefJumpNav({ activeId, onSelect }: BriefJumpNavProps) {
  return (
    <nav className="brief-jump-nav" aria-label="Brief sections">
      <ul>
        {SECTIONS.map((s) => (
          <li key={s.id}>
            <button
              type="button"
              className={activeId === s.id ? "active" : ""}
              onClick={() => onSelect(s.id)}
            >
              {s.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
