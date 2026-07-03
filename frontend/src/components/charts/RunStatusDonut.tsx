import { Cell, Pie, PieChart, Tooltip } from "recharts";
import { ChartCard, statusColor, useChartColors } from "./ChartTheme";

type RunStatusDonutProps = {
  counts?: Record<string, number>;
};

function toRows(counts: Record<string, number>) {
  return Object.entries(counts).map(([name, value]) => ({ name, value }));
}

export function RunStatusDonut({ counts = {} }: RunStatusDonutProps) {
  const palette = useChartColors();
  const rows = toRows(counts);
  const total = rows.reduce((sum, row) => sum + row.value, 0);
  const ariaLabel =
    total > 0
      ? `Run status distribution: ${rows.map((r) => `${r.name} ${r.value}`).join(", ")}`
      : "Run status distribution: no runs recorded";

  return (
    <ChartCard
      title="Run status"
      ariaLabel={ariaLabel}
      fallback={
        <table className="chart-data-fallback">
          <caption>Run status counts</caption>
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
                <td colSpan={2}>No runs</td>
              </tr>
            )}
          </tbody>
        </table>
      }
    >
      <PieChart>
        <Pie
          data={rows.length ? rows : [{ name: "empty", value: 1 }]}
          dataKey="value"
          nameKey="name"
          innerRadius="58%"
          outerRadius="82%"
          paddingAngle={rows.length > 1 ? 2 : 0}
          stroke="none"
        >
          {(rows.length ? rows : [{ name: "empty", value: 1 }]).map((entry) => (
            <Cell
              key={entry.name}
              fill={rows.length ? statusColor(entry.name, palette) : palette.muted}
            />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number, name: string) => [value, name]}
          contentStyle={{
            background: palette.surface,
            border: `1px solid ${palette.muted}`,
            borderRadius: 8,
            color: palette.text,
          }}
        />
      </PieChart>
    </ChartCard>
  );
}
