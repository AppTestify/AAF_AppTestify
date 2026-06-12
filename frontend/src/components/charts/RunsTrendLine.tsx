import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { RunsTimeseries } from "../../api";
import { mapRunsTimeseriesToChartData, RUN_STATUS_COLORS } from "../../lib/chartMappers";
import { ChartCard, useChartColors } from "./ChartTheme";

type RunsTrendLineProps = {
  data: RunsTimeseries | null;
  loading?: boolean;
};

const SERIES = [
  { key: "succeeded", label: "Succeeded" },
  { key: "failed", label: "Failed" },
  { key: "running", label: "Running" },
  { key: "queued", label: "Queued" },
] as const;

export function RunsTrendLine({ data, loading = false }: RunsTrendLineProps) {
  const navigate = useNavigate();
  const palette = useChartColors();
  const chartData = useMemo(
    () => (data ? mapRunsTimeseriesToChartData(data.series) : []),
    [data]
  );

  const drillDown = (status: string) => {
    navigate(`/app/runs?status=${encodeURIComponent(status)}`);
  };

  const ariaLabel =
    chartData.length > 0
      ? `Runs trend over ${data?.days ?? 7} days`
      : "Runs trend: no data in selected window";

  return (
    <ChartCard
      title="Runs trend (7d)"
      loading={loading}
      height={220}
      ariaLabel={ariaLabel}
      fallback={
        <table className="chart-data-fallback">
          <caption>Daily run counts by status</caption>
          <thead>
            <tr>
              <th scope="col">Date</th>
              {SERIES.map((s) => (
                <th key={s.key} scope="col">
                  {s.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {chartData.map((row) => (
              <tr key={row.date}>
                <th scope="row">{row.label}</th>
                {SERIES.map((s) => (
                  <td key={s.key}>
                    <button type="button" className="chart-drill-link" onClick={() => drillDown(s.key)}>
                      {row[s.key]}
                    </button>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      }
    >
      <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={palette.muted} opacity={0.25} />
        <XAxis dataKey="label" tick={{ fill: palette.muted, fontSize: 11 }} />
        <YAxis allowDecimals={false} tick={{ fill: palette.muted, fontSize: 11 }} width={28} />
        <Tooltip
          contentStyle={{
            background: palette.surface,
            border: `1px solid ${palette.muted}`,
            borderRadius: 8,
            color: palette.text,
            fontSize: 12,
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, cursor: "pointer" }}
          onClick={(entry) => {
            const status = String(entry.dataKey ?? "");
            if (status) drillDown(status);
          }}
        />
        {SERIES.map(({ key, label }) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            name={label}
            stroke={RUN_STATUS_COLORS[key]}
            strokeWidth={2}
            dot={{ r: 3, cursor: "pointer" }}
            activeDot={{
              r: 5,
              cursor: "pointer",
              onClick: () => drillDown(key),
            }}
          />
        ))}
      </LineChart>
    </ChartCard>
  );
}
