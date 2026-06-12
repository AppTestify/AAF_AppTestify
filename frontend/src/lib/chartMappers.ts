import type { RunsTimeseries } from "../api";

export const RUN_STATUS_ORDER = ["succeeded", "failed", "running", "queued"] as const;

export type RunStatusKey = (typeof RUN_STATUS_ORDER)[number] | string;

export const RUN_STATUS_COLORS: Record<string, string> = {
  succeeded: "#10b981",
  failed: "#ef4444",
  running: "#f59e0b",
  queued: "#3b82f6",
};

export type StatusChartPoint = {
  status: string;
  count: number;
  fill: string;
};

export type TimeseriesChartPoint = {
  date: string;
  label: string;
  succeeded: number;
  failed: number;
  running: number;
  queued: number;
  total: number;
};

function formatDayLabel(isoDate: string): string {
  const d = new Date(`${isoDate}T12:00:00`);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function mapStatusCountsToChartData(counts: Record<string, number>): StatusChartPoint[] {
  const keys = new Set([...RUN_STATUS_ORDER, ...Object.keys(counts)]);
  return [...keys]
    .map((status) => ({
      status,
      count: counts[status] ?? 0,
      fill: RUN_STATUS_COLORS[status] ?? "#94a3b8",
    }))
    .filter((row) => row.count > 0 || RUN_STATUS_ORDER.includes(row.status as RunStatusKey))
    .sort((a, b) => {
      const ai = RUN_STATUS_ORDER.indexOf(a.status as RunStatusKey);
      const bi = RUN_STATUS_ORDER.indexOf(b.status as RunStatusKey);
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    });
}

export function mapRunsTimeseriesToChartData(series: RunsTimeseries["series"]): TimeseriesChartPoint[] {
  return series.map((point) => {
    const succeeded = point.counts.succeeded ?? 0;
    const failed = point.counts.failed ?? 0;
    const running = point.counts.running ?? 0;
    const queued = point.counts.queued ?? 0;
    return {
      date: point.date,
      label: formatDayLabel(point.date),
      succeeded,
      failed,
      running,
      queued,
      total: succeeded + failed + running + queued,
    };
  });
}

export function aggregateTimeseriesByStatus(series: RunsTimeseries["series"]): Record<string, number> {
  const totals: Record<string, number> = {};
  for (const point of series) {
    for (const [status, count] of Object.entries(point.counts)) {
      totals[status] = (totals[status] ?? 0) + count;
    }
  }
  return totals;
}
