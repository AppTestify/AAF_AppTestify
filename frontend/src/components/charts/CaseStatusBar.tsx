import { Bar, BarChart, CartesianGrid, Cell, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard, statusColor, useChartColors } from "./ChartTheme";

type CaseStatusBarProps = {
  counts?: Record<string, number>;
};

function toRows(counts: Record<string, number>) {
  return Object.entries(counts).map(([name, value]) => ({ name, value }));
}

export function CaseStatusBar({ counts = {} }: CaseStatusBarProps) {
  const palette = useChartColors();
  const rows = toRows(counts);
  const ariaLabel =
    rows.length > 0
      ? `Case status counts: ${rows.map((r) => `${r.name} ${r.value}`).join(", ")}`
      : "Case status counts: no cases recorded";

  return (
    <ChartCard
      title="Case status"
      ariaLabel={ariaLabel}
      height={220}
      fallback={
        <table className="chart-data-fallback">
          <caption>Case status counts</caption>
          <thead>
            <tr>
              <th scope="col">Status</th>
              <th scope="col">Count</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((row) => (
                <tr key={row.name}>
                  <td>{row.name}</td>
                  <td>{row.value}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={2}>No cases</td>
              </tr>
            )}
          </tbody>
        </table>
      }
    >
      <BarChart data={rows.length ? rows : [{ name: "—", value: 0 }]} layout="vertical" margin={{ left: 4, right: 12 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={palette.muted} opacity={0.25} horizontal={false} />
        <XAxis type="number" tick={{ fill: palette.muted, fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis
          type="category"
          dataKey="name"
          width={72}
          tick={{ fill: palette.muted, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={(value: number) => [value, "Cases"]}
          contentStyle={{
            background: palette.surface,
            border: `1px solid ${palette.muted}`,
            borderRadius: 8,
            color: palette.text,
          }}
        />
        <Bar dataKey="value" radius={[0, 6, 6, 0]} maxBarSize={18}>
          {rows.map((entry) => (
            <Cell key={entry.name} fill={statusColor(entry.name, palette)} />
          ))}
        </Bar>
      </BarChart>
    </ChartCard>
  );
}
