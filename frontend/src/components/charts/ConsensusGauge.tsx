import { Cell, Pie, PieChart, Tooltip } from "recharts";
import { ChartCard, useChartColors } from "./ChartTheme";

type ConsensusGaugeProps = {
  score?: number | null;
  conflictRate?: number | null;
};

export function ConsensusGauge({ score, conflictRate }: ConsensusGaugeProps) {
  const palette = useChartColors();
  const normalized = score == null ? 0 : Math.min(1, Math.max(0, score));
  const pct = Math.round(normalized * 100);
  const gaugeData = [
    { name: "score", value: normalized },
    { name: "remainder", value: 1 - normalized },
  ];
  const tone = normalized >= 0.7 ? palette.good : normalized >= 0.45 ? palette.warn : palette.bad;
  const ariaLabel =
    score == null
      ? "Consensus score unavailable"
      : `Consensus score ${pct} percent${conflictRate != null ? `, conflict rate ${Math.round(conflictRate * 100)} percent` : ""}`;

  return (
    <ChartCard
      title="Consensus"
      ariaLabel={ariaLabel}
      fallback={
        <table className="chart-data-fallback">
          <caption>Consensus metrics</caption>
          <tbody>
            <tr>
              <th scope="row">Score</th>
              <td>{score == null ? "—" : normalized.toFixed(2)}</td>
            </tr>
            {conflictRate != null ? (
              <tr>
                <th scope="row">Conflict rate</th>
                <td>{conflictRate.toFixed(2)}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      }
    >
      <PieChart>
        <Pie
          data={gaugeData}
          dataKey="value"
          startAngle={180}
          endAngle={0}
          innerRadius="62%"
          outerRadius="88%"
          cx="50%"
          cy="78%"
          stroke="none"
        >
          <Cell fill={tone} />
          <Cell fill={palette.surface} />
        </Pie>
        <Tooltip
          formatter={() => [score == null ? "—" : normalized.toFixed(2), "Consensus"]}
          contentStyle={{
            background: palette.surface,
            border: `1px solid ${palette.muted}`,
            borderRadius: 8,
            color: palette.text,
          }}
        />
        <text x="50%" y="72%" textAnchor="middle" dominantBaseline="middle" fill={palette.text} fontSize={22} fontWeight={700}>
          {score == null ? "—" : `${pct}%`}
        </text>
      </PieChart>
    </ChartCard>
  );
}
