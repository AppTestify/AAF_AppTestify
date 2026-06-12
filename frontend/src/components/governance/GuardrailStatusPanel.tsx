import type { GuardrailReport, LlmBudgetStatus, LlmCostSnapshot } from "../../api";

const GUARD_LABELS: Record<string, string> = {
  pm_prompt_guard: "PM prompt",
  evidence_guard: "Evidence",
  tool_scope_guard: "Tool scope",
  agent_output_guard: "Agent output",
  brief_output_guard: "Brief output",
  budget_cap: "Budget cap",
};

function stageStatus(stage: {
  passed: boolean;
  blocked?: boolean;
  violations?: { severity: string }[];
}): "pass" | "warn" | "fail" {
  if (stage.blocked || stage.passed === false) return "fail";
  const hasWarn = (stage.violations ?? []).some((v) => v.severity === "warn");
  if (hasWarn) return "warn";
  return "pass";
}

type GuardrailStatusPanelProps = {
  guardrails?: GuardrailReport | null;
  llmCost?: LlmCostSnapshot | null;
  llmBudget?: LlmBudgetStatus | null;
  compact?: boolean;
};

export function GuardrailStatusPanel({ guardrails, llmCost, llmBudget, compact = false }: GuardrailStatusPanelProps) {
  if (!guardrails?.enabled && !llmCost?.totals?.cost_usd && !llmBudget) return null;

  const order = guardrails?.pipeline_order ?? [];
  const stageByName = new Map((guardrails?.stages ?? []).map((s) => [s.guard_name, s]));
  const orderedStages = order.length
    ? order.map((name) => stageByName.get(name)).filter(Boolean)
    : guardrails?.stages ?? [];

  const costUsd = llmCost?.totals?.cost_usd ?? 0;
  const budgetUsd = llmBudget?.budget_usd;
  const spentUsd = llmBudget?.spent_usd;
  const utilization = llmBudget?.utilization;

  return (
    <section className={`guardrail-panel ${compact ? "guardrail-panel--compact" : ""}`}>
      <div className="guardrail-panel-head">
        <div>
          <p className="gov-hub-eyebrow">Run integrity</p>
          <h3 style={{ margin: 0 }}>Guardrails &amp; cost</h3>
        </div>
        <div className="guardrail-panel-badges">
          {guardrails ? (
            <span className={`guardrail-chip guardrail-chip--${guardrails.all_passed ? "pass" : "fail"}`}>
              {guardrails.all_passed ? "All checks passed" : "Issues detected"}
            </span>
          ) : null}
          {costUsd > 0 ? (
            <span className="guardrail-chip guardrail-chip--neutral">LLM ${costUsd.toFixed(4)}</span>
          ) : null}
        </div>
      </div>

      {orderedStages.length > 0 ? (
        <ul className="guardrail-stage-list">
          {orderedStages.map((stage) => {
            if (!stage) return null;
            const status = stageStatus(stage);
            const label = GUARD_LABELS[stage.guard_name] ?? stage.guard_name;
            return (
              <li key={stage.guard_name} className={`guardrail-stage guardrail-stage--${status}`}>
                <span className="guardrail-stage-label">{label}</span>
                <span className={`guardrail-stage-chip guardrail-stage-chip--${status}`}>
                  {status === "pass" ? "Pass" : status === "warn" ? "Warn" : "Fail"}
                </span>
                {!compact && (stage.violations?.length ?? 0) > 0 ? (
                  <ul className="guardrail-violation-list">
                    {stage.violations!.map((v, i) => (
                      <li key={i}>
                        <span className="mono">{v.rule}</span> — {v.message}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}

      {guardrails?.summary ? (
        <p className="field-hint guardrail-summary">
          {guardrails.summary.passed} passed · {guardrails.summary.warned} warnings · {guardrails.summary.blocked} blocked
        </p>
      ) : null}

      {llmCost?.totals ? (
        <div className="guardrail-cost-row">
          <span>
            Tokens: {llmCost.totals.prompt_tokens + llmCost.totals.completion_tokens} ({llmCost.totals.call_count} calls)
          </span>
          {Object.keys(llmCost.by_phase ?? {}).length > 0 ? (
            <span className="field-hint">
              By phase:{" "}
              {Object.entries(llmCost.by_phase!)
                .map(([k, v]) => `${k} $${v.toFixed(4)}`)
                .join(" · ")}
            </span>
          ) : null}
        </div>
      ) : null}

      {budgetUsd != null && spentUsd != null ? (
        <div className="guardrail-budget-row">
          <span>
            Monthly budget: ${spentUsd.toFixed(2)} / ${budgetUsd.toFixed(2)}
            {utilization != null ? ` (${Math.round(utilization * 100)}%)` : ""}
          </span>
          {llmBudget?.status ? (
            <span className={`guardrail-chip guardrail-chip--${llmBudget.status === "ok" ? "pass" : "warn"}`}>
              {llmBudget.status}
            </span>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
