import { describe, expect, it } from "vitest";
import { deriveDecisionFlow, isLiveTrace, parseRunResult } from "./governancePresentation";

describe("governancePresentation", () => {
  it("marks live trace when run is running", () => {
    expect(isLiveTrace("running", null)).toBe(true);
    expect(isLiveTrace("succeeded", new Date().toISOString())).toBe(true);
  });

  it("returns default flow without parsed run", () => {
    const steps = deriveDecisionFlow(null);
    expect(steps.length).toBeGreaterThan(4);
    expect(steps.some((s) => s.id === "secops")).toBe(true);
    expect(steps.some((s) => s.id === "brief")).toBe(true);
  });

  it("parses guardrails and llm_cost from result_json", () => {
    const parsed = parseRunResult({
      agent_opinions: [],
      utility: { recommended_action: "observe", utility_score: 0.5, global_utility: 0.5, perf_index: 0.5, cost_index: 0.5, risk_index: 0.5, scores_by_action: {}, weights_used: {} },
      consensus: { consensus_score: 0.6, theme_counts: {}, notes: "" },
      guardrails: { enabled: true, pipeline_order: ["pm_prompt_guard"], stages: [], all_passed: true, summary: { stage_count: 1, passed: 1, warned: 0, blocked: 0 } },
      llm_cost: { totals: { prompt_tokens: 10, completion_tokens: 5, cost_usd: 0.001, call_count: 1 } },
    });
    expect(parsed?.guardrails?.enabled).toBe(true);
    expect(parsed?.llm_cost?.totals?.cost_usd).toBe(0.001);
  });
});
