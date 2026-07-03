import { Bar, BarChart, CartesianGrid, Cell, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard, statusColor, useChartColors } from "./ChartTheme";

type CountBarChartProps = {
  title: string;
  counts?: Record<string, number>;
  horizontal?: boolean;
};

function toRows(counts: Record<string, number>) {
  return Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

export function CountBarChart({ title, counts = {}, horizontal = false }: CountBarChartProps) {
  const palette = useChartColors();
  const rows = toRows(counts);
  const total = rows.reduce((sum, row) => sum + row.value, 0);
  const ariaLabel =
    total > 0
      ? `${title}: ${rows.map((r) => `${r.name} ${r.value}`).join(", ")}`
      : `${title}: no data recorded`;

  return (
    <ChartCard
      title={title}
      ariaLabel={ariaLabel}
      height={horizontal ? 220 : 240}
      fallback={
        <table className="chart-data-fallback">
          <caption>{title}</caption>
          <thead>
            <tr>
              <th scope="col">Category</th>
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
                <td colSpan={2}>No data</td>
              </tr>
            )}
          </tbody>
        </table>
      }
    >
      <BarChart
        data={rows.length ? rows : [{ name: "—", value: 0 }]}
        layout={horizontal ? "vertical" : "horizontal"}
        margin={horizontal ? { left: 4, right: 12 } : { left: -8, right: 12, bottom: 4 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={palette.muted} opacity={0.25} vertical={!horizontal} horizontal={horizontal} />
        {horizontal ? (
          <>
            <XAxis type="number" tick={{ fill: palette.muted, fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
            <YAxis
              type="category"
              dataKey="name"
              width={110}
              tick={{ fill: palette.muted, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
          </>
        ) : (
          <>
            <XAxis
              dataKey="name"
              tick={{ fill: palette.muted, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              interval={0}
              angle={-18}
              textAnchor="end"
              height={56}
            />
            <YAxis tick={{ fill: palette.muted, fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
          </>
        )}
        <Tooltip
          itemStyle={{ color: palette.text }}
          formatter={(value: number) => [value, "Count"]}
          contentStyle={{
            background: palette.surface,
            border: `1px solid ${palette.muted}`,
            borderRadius: 8,
            color: palette.text,
          }}
        />
        <Bar dataKey="value" radius={horizontal ? [0, 6, 6, 0] : [4, 4, 0, 0]} maxBarSize={horizontal ? 18 : 42}>
          {rows.map((entry) => (
            <Cell key={entry.name} fill={statusColor(entry.name, palette)} />
          ))}
        </Bar>
      </BarChart>
    </ChartCard>
  );
}
