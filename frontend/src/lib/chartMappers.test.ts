import { describe, expect, it } from "vitest";
import {
  aggregateTimeseriesByStatus,
  mapRunsTimeseriesToChartData,
  mapStatusCountsToChartData,
} from "./chartMappers";

describe("chartMappers", () => {
  it("maps status counts to sorted chart rows with colors", () => {
    const rows = mapStatusCountsToChartData({ failed: 2, succeeded: 5, running: 1 });
    expect(rows.find((r) => r.status === "succeeded")?.count).toBe(5);
    expect(rows.find((r) => r.status === "failed")?.fill).toBe("#ef4444");
    expect(rows[0].status).toBe("succeeded");
  });

  it("maps timeseries API payload to line chart points", () => {
    const points = mapRunsTimeseriesToChartData([
      { date: "2026-06-10", counts: { succeeded: 3, failed: 1 } },
      { date: "2026-06-11", counts: { succeeded: 2, queued: 1 } },
    ]);

    expect(points).toHaveLength(2);
    expect(points[0].succeeded).toBe(3);
    expect(points[0].failed).toBe(1);
    expect(points[0].queued).toBe(0);
    expect(points[1].total).toBe(3);
    expect(points[0].label).toMatch(/Jun/);
  });

  it("aggregates daily counts by status", () => {
    const totals = aggregateTimeseriesByStatus([
      { date: "2026-06-10", counts: { succeeded: 2, failed: 1 } },
      { date: "2026-06-11", counts: { succeeded: 1, failed: 2 } },
    ]);
    expect(totals).toEqual({ succeeded: 3, failed: 3 });
  });
});
