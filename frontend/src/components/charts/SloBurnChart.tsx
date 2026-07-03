import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Tooltip, XAxis, YAxis } from "recharts";
import type { ObservabilitySummary } from "../../api";
import { ChartCard, useChartColors } from "./ChartTheme";

type SloBurnChartProps = {
  slo: ObservabilitySummary["slo_burn_rate"] | null | undefined;
  loading?: boolean;
};

export function SloBurnChart({ slo, loading = false }: SloBurnChartProps) {
  const navigate = useNavigate();
  const palette = useChartColors();

  const chartData = useMemo(() => {
    if (!slo) return [];
    return [
      { window: "Short", burnRate: slo.short_burn_rate, errorRate: slo.short_error_rate },
      { window: "Long", burnRate: slo.long_burn_rate, errorRate: slo.long_error_rate },
    ];
  }, [slo]);

  const stateColor =
    slo?.state === "critical" ? palette.bad : slo?.state === "warning" ? palette.warn : palette.good;

  const drillDown = () => navigate("/app/runs?status=failed");

  return (
    <ChartCard
      title={`SLO burn (${slo?.state ?? "—"})`}
      loading={loading}
      height={220}
      ariaLabel={`SLO burn state ${slo?.state ?? "unknown"}`}
      fallback={
        <table className="chart-data-fallback">
          <caption>SLO burn metrics</caption>
          <thead>
            <tr>
              <th scope="col">Window</th>
              <th scope="col">Burn rate</th>
              <th scope="col">Error rate</th>
            </tr>
          </thead>
          <tbody>
            {chartData.map((row) => (
              <tr key={row.window}>
                <th scope="row">{row.window}</th>
                <td>
                  <button type="button" className="chart-drill-link" onClick={drillDown}>
                    {row.burnRate.toFixed(3)}
                  </button>
                </td>
                <td>{row.errorRate.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      }
    >
      <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={palette.muted} opacity={0.25} />
        <XAxis dataKey="window" tick={{ fill: palette.muted, fontSize: 11 }} />
        <YAxis tick={{ fill: palette.muted, fontSize: 11 }} width={36} />
        <Tooltip
          itemStyle={{ color: palette.text }}
          formatter={(value: number, name: string) => [
            name === "burnRate" ? value.toFixed(3) : value.toFixed(4),
            name === "burnRate" ? "Burn rate" : "Error rate",
          ]}
          contentStyle={{
            background: palette.surface,
            border: `1px solid ${palette.muted}`,
            borderRadius: 8,
            color: palette.text,
            fontSize: 12,
          }}
        />
        <Bar dataKey="burnRate" name="Burn rate" radius={[6, 6, 0, 0]} cursor="pointer" onClick={() => drillDown()}>
          {chartData.map((entry) => (
            <Cell key={entry.window} fill={stateColor} />
          ))}
        </Bar>
      </BarChart>
    </ChartCard>
  );
}
