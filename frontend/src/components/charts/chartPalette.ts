export const CHART_COLORS = {
  accent: "#1d4ed8",
  good: "#047857",
  warn: "#b45309",
  bad: "#b91c1c",
  muted: "#64748b",
  surface: "#e2e8f0",
} as const;

export const CHART_PALETTE = [
  CHART_COLORS.accent,
  CHART_COLORS.good,
  CHART_COLORS.warn,
  CHART_COLORS.bad,
  "#6366f1",
  "#0d9488",
  CHART_COLORS.muted,
] as const;

export function colorForLabel(label: string): string {
  const key = label.toLowerCase();
  if (key.includes("succeed") || key.includes("approved") || key.includes("go")) return CHART_COLORS.good;
  if (key.includes("fail") || key.includes("critical") || key.includes("block")) return CHART_COLORS.bad;
  if (key.includes("run") || key.includes("warn") || key.includes("high") || key.includes("review")) {
    return CHART_COLORS.warn;
  }
  return CHART_COLORS.accent;
}

export function countsToChartData(counts: Record<string, number>) {
  return Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}
