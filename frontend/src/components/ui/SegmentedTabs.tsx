export type SegmentedTabItem = {
  id: string;
  label: string;
  disabled?: boolean;
};

type SegmentedTabsProps = {
  tabs: SegmentedTabItem[];
  activeId: string;
  onChange: (id: string) => void;
  className?: string;
  "aria-label"?: string;
};

export function SegmentedTabs({
  tabs,
  activeId,
  onChange,
  className = "",
  "aria-label": ariaLabel = "Section tabs",
}: SegmentedTabsProps) {
  return (
    <div className={`segmented-tabs ${className}`.trim()} role="tablist" aria-label={ariaLabel}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={activeId === tab.id}
          className={activeId === tab.id ? "active" : ""}
          disabled={tab.disabled}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
