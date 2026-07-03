import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

export type DonutSegment = {
  name: string;
  value: number;
  color?: string;
};

const DEFAULT_COLORS = ["#3d8bfd", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#64748b"];

type DonutChartProps = {
  data: DonutSegment[];
  title?: string;
  emptyMessage?: string;
  height?: number;
};

export function DonutChart({ data, title, emptyMessage = "No data yet.", height = 200 }: DonutChartProps) {
  const filtered = data.filter((d) => d.value > 0);
  const total = filtered.reduce((sum, d) => sum + d.value, 0);

  if (total === 0) {
    return (
      <div className="chart-donut chart-donut--empty">
        {title ? <h3 className="chart-donut-title">{title}</h3> : null}
        <p className="workspace-meta">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="chart-donut">
      {title ? <h3 className="chart-donut-title">{title}</h3> : null}
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={filtered}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius="58%"
            outerRadius="82%"
            paddingAngle={2}
          >
            {filtered.map((entry, i) => (
              <Cell key={entry.name} fill={entry.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value: number) => [value, "Count"]} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
