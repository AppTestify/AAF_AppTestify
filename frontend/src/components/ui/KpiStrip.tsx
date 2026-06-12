export type KpiItem = {
  label: string;
  value: React.ReactNode;
  tone?: "default" | "good" | "warn" | "bad";
};

type KpiStripProps = {
  items?: KpiItem[];
  loading?: boolean;
  skeletonCount?: number;
  className?: string;
};

export function KpiStrip({
  items = [],
  loading = false,
  skeletonCount = 4,
  className = "",
}: KpiStripProps) {
  if (loading) {
    return (
      <div
        className={`workspace-kpi-strip ${className}`.trim()}
        aria-busy="true"
        aria-label="Loading metrics"
      >
        {Array.from({ length: skeletonCount }, (_, i) => (
          <div key={i} className="metric kpi-skeleton">
            <div className="kpi-skeleton-label" aria-hidden="true" />
            <div className="kpi-skeleton-value" aria-hidden="true" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={`workspace-kpi-strip ${className}`.trim()}>
      {items.map((item) => (
        <div key={item.label} className="metric">
          <div className="label">{item.label}</div>
          <div className={`value${item.tone && item.tone !== "default" ? ` ${item.tone}` : ""}`}>{item.value}</div>
        </div>
      ))}
    </div>
  );
}
