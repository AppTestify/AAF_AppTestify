import { Cell, Pie, PieChart, Tooltip } from "recharts";
import type { DashboardSummary } from "../../api";
import { ChartCard, useChartColors } from "./ChartTheme";

type ConnectorHealthDonutProps = {
  connectors?: DashboardSummary["connector_health"];
};

function deriveHealthSlices(connectors: DashboardSummary["connector_health"]) {
  let healthy = 0;
  let unhealthy = 0;
  let unknown = 0;

  for (const c of connectors) {
    if (!c.enabled) {
      unknown += 1;
      continue;
    }
    if (c.last_validation_ok === true) healthy += 1;
    else if (c.last_validation_ok === false) unhealthy += 1;
    else unknown += 1;
  }

  return [
    { name: "Healthy", value: healthy },
    { name: "Unhealthy", value: unhealthy },
    { name: "Unknown", value: unknown },
  ].filter((row) => row.value > 0);
}

export function ConnectorHealthDonut({ connectors = [] }: ConnectorHealthDonutProps) {
  const palette = useChartColors();
  const slices = deriveHealthSlices(connectors);
  const sliceColors: Record<string, string> = {
    Healthy: palette.good,
    Unhealthy: palette.bad,
    Unknown: palette.warn,
  };
  const ariaLabel =
    slices.length > 0
      ? `Connector health: ${slices.map((s) => `${s.name} ${s.value}`).join(", ")}`
      : "Connector health: no connectors configured";

  return (
    <ChartCard
      title="Connector health"
      ariaLabel={ariaLabel}
      fallback={
        <table className="chart-data-fallback">
          <caption>Connector validation health</caption>
          <thead>
            <tr>
              <th scope="col">Connector</th>
              <th scope="col">Enabled</th>
              <th scope="col">Validation</th>
            </tr>
          </thead>
          <tbody>
            {connectors.length ? (
              connectors.map((c) => (
                <tr key={c.connector_name}>
                  <td>{c.connector_name}</td>
                  <td>{c.enabled ? "Yes" : "No"}</td>
                  <td>
                    {c.last_validation_ok == null ? "Unknown" : c.last_validation_ok ? "OK" : "Failed"}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={3}>No connectors</td>
              </tr>
            )}
          </tbody>
        </table>
      }
    >
      <PieChart>
        <Pie
          data={slices.length ? slices : [{ name: "No data", value: 1 }]}
          dataKey="value"
          nameKey="name"
          innerRadius="58%"
          outerRadius="82%"
          paddingAngle={slices.length > 1 ? 2 : 0}
          stroke="none"
        >
          {(slices.length ? slices : [{ name: "No data", value: 1 }]).map((entry) => (
            <Cell key={entry.name} fill={sliceColors[entry.name] ?? palette.muted} />
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
