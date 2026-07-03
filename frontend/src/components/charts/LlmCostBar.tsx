import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Tooltip, XAxis, YAxis } from "recharts";
import type { ObservabilitySummary } from "../../api";
import { ChartCard, useChartColors } from "./ChartTheme";

type LlmCostBarProps = {
  invocation: ObservabilitySummary["llm_invocation"] | null | undefined;
  loading?: boolean;
};

export function LlmCostBar({ invocation, loading = false }: LlmCostBarProps) {
  const navigate = useNavigate();
  const palette = useChartColors();

  const chartData = useMemo(() => {
    if (!invocation) return [];
    return [
      { label: "OK", count: invocation.ok_total, status: "succeeded", fill: palette.good },
      { label: "Degraded", count: invocation.degraded_total, status: "failed", fill: palette.warn },
    ];
  }, [invocation, palette.good, palette.warn]);

  const drillDown = (status: string) => navigate(`/app/runs?status=${encodeURIComponent(status)}`);

  return (
    <ChartCard
      title="LLM invocations"
      loading={loading}
      height={220}
      ariaLabel="LLM invocation outcomes"
      fallback={
        <table className="chart-data-fallback">
          <caption>LLM invocation counts</caption>
          <thead>
            <tr>
              <th scope="col">Outcome</th>
              <th scope="col">Count</th>
            </tr>
          </thead>
          <tbody>
            {chartData.map((row) => (
              <tr key={row.label}>
                <th scope="row">{row.label}</th>
                <td>
                  <button type="button" className="chart-drill-link" onClick={() => drillDown(row.status)}>
                    {row.count}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      }
    >
      <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
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
        <Bar
          dataKey="count"
          name="Invocations"
          radius={[6, 6, 0, 0]}
          cursor="pointer"
          onClick={(entry) => drillDown(String(entry.status ?? "succeeded"))}
        >
          {chartData.map((entry) => (
            <Cell key={entry.label} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ChartCard>
  );
}
