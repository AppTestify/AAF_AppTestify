import type { ReactNode } from "react";
import { ResponsiveContainer } from "recharts";

export const CHART_COLORS = {
  accent: "#3d8bfd",
  good: "#10b981",
  warn: "#f59e0b",
  bad: "#ef4444",
  muted: "#94a3b8",
  surface: "var(--surface)",
  text: "var(--text)",
  grid: "color-mix(in srgb, var(--border) 80%, transparent)",
} as const;

export type ChartPalette = {
  accent: string;
  good: string;
  warn: string;
  bad: string;
  muted: string;
  surface: string;
  text: string;
};

export function useChartColors(): ChartPalette {
  if (typeof document === "undefined") {
    return {
      accent: CHART_COLORS.accent,
      good: CHART_COLORS.good,
      warn: CHART_COLORS.warn,
      bad: CHART_COLORS.bad,
      muted: CHART_COLORS.muted,
      surface: "#1e293b",
      text: "#f8fafc",
    };
  }

  const styles = getComputedStyle(document.documentElement);
  const read = (name: string, fallback: string) => styles.getPropertyValue(name).trim() || fallback;

  return {
    accent: read("--accent", CHART_COLORS.accent),
    good: read("--success", CHART_COLORS.good),
    warn: read("--warning", CHART_COLORS.warn),
    bad: read("--danger", CHART_COLORS.bad),
    muted: read("--muted", CHART_COLORS.muted),
    surface: read("--surface", "#1e293b"),
    text: read("--text", "#f8fafc"),
  };
}

export function statusColor(name: string, palette: ChartPalette): string {
  const key = name.toLowerCase();
  if (key.includes("succeed") || key.includes("approved") || key.includes("healthy") || key === "go") {
    return palette.good;
  }
  if (key.includes("fail") || key.includes("critical") || key.includes("unhealthy") || key.includes("block")) {
    return palette.bad;
  }
  if (
    key.includes("running") ||
    key.includes("warn") ||
    key.includes("high") ||
    key.includes("review") ||
    key.includes("unknown") ||
    key.includes("medium")
  ) {
    return palette.warn;
  }
  return palette.accent;
}

type ChartCardProps = {
  title: string;
  children: ReactNode;
  loading?: boolean;
  className?: string;
  ariaLabel?: string;
  height?: number;
  fallback?: ReactNode;
};

export function ChartCard({
  title,
  children,
  loading = false,
  className = "",
  ariaLabel,
  height = 200,
  fallback,
}: ChartCardProps) {
  return (
    <div
      className={`chart-card ${className}`.trim()}
      aria-busy={loading || undefined}
      role={ariaLabel ? "img" : undefined}
      aria-label={ariaLabel}
    >
      <h3 className="chart-card-title">{title}</h3>
      {loading ? (
        <div className="chart-skeleton" aria-hidden="true" />
      ) : (
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={height}>
            {children}
          </ResponsiveContainer>
        </div>
      )}
      {fallback ? <div className="sr-only chart-fallback">{fallback}</div> : null}
    </div>
  );
}
