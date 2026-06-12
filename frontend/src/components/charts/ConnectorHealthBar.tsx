import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DashboardSummary } from "../../api";

const STATUS_COLORS: Record<string, string> = {
  healthy: "#22c55e",
  failing: "#ef4444",
  unknown: "#94a3b8",
  disabled: "#cbd5e1",
};

type ConnectorHealthBarProps = {
  connectors: DashboardSummary["connector_health"];
  title?: string;
};

export function ConnectorHealthBar({ connectors, title = "Connector validation" }: ConnectorHealthBarProps) {
  const rows = connectors.map((c) => {
    let status = "unknown";
    if (!c.enabled) status = "disabled";
    else if (c.last_validation_ok === true) status = "healthy";
    else if (c.last_validation_ok === false) status = "failing";
    return {
      name: c.connector_name,
      score: c.enabled ? (c.last_validation_ok === true ? 100 : c.last_validation_ok === false ? 25 : 50) : 0,
      status,
      label: !c.enabled ? "disabled" : c.last_validation_ok === true ? "healthy" : c.last_validation_ok === false ? "failing" : "unknown",
    };
  });

  if (rows.length === 0) {
    return (
      <div className="chart-bar-timeline chart-bar-timeline--empty">
        <h3 className="chart-donut-title">{title}</h3>
        <p className="workspace-meta">No connectors configured.</p>
      </div>
    );
  }

  return (
    <div className="chart-bar-timeline">
      <h3 className="chart-donut-title">{title}</h3>
      <ResponsiveContainer width="100%" height={Math.max(160, rows.length * 36)}>
        <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
          <XAxis type="number" domain={[0, 100]} hide />
          <YAxis type="category" dataKey="name" width={72} tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(_value: number, _name: string, item: { payload?: { label?: string } }) => [
              item.payload?.label ?? "unknown",
              "Status",
            ]}
          />
          <Bar dataKey="score" radius={[0, 6, 6, 0]} barSize={18}>
            {rows.map((row) => (
              <Cell key={row.name} fill={STATUS_COLORS[row.status] ?? STATUS_COLORS.unknown} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
