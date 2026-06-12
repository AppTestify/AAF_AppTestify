import { describe, expect, it } from "vitest";
import {
  countToolCallsFromRawSignals,
  deriveDecisionFlow,
  deriveTransportFromRawSignals,
  formatActionLabel,
  formatToolCallLabel,
  isHoldReleaseAction,
  isLiveTrace,
  parseGovernanceRunResult,
  parseRunResult,
} from "./governancePresentation";
import type { GovernanceRunV1 } from "../api";

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
    expect(steps.some((s) => s.id === "intent")).toBe(false);
  });

  it("inserts LLM Intent Router step when pipeline_phase is 3", () => {
    const run: GovernanceRunV1 = {
      id: 1,
      tenant_id: 1,
      status: "succeeded",
      prompt: "Should we release today?",
      prompt_id: null,
      portfolio_project_id: null,
      retry_count: 0,
      error_message: null,
      runtime_config_json: {},
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      finished_at: new Date().toISOString(),
      result_json: {
        prompt: "Should we release today?",
        agent_opinions: [],
        consensus: { consensus_score: 0.87, theme_counts: {}, notes: "" },
        utility: {
          recommended_action: "hold_release",
          utility_score: 0.8,
          global_utility: 0.8,
          perf_index: 0.7,
          cost_index: 0.6,
          risk_index: 0.4,
          scores_by_action: {},
          weights_used: {},
        },
        rar: { rar_triggered: false, rar_loops: 0, consensus_before: 0.87, consensus_after: 0.87 },
        explainability: { xi_score: 0.8, checks: {} },
        explanation: "Hold release",
        connectors_used: [],
        raw_evidence_by_connector: {},
        normalized_evidence: [],
        pipeline_phase: 3,
        intent: { category: "release_readiness" },
        decision_framing: {
          intent_category: "release_readiness",
          orchestration: { recommended_action: "hold_release", consensus_score: 0.87 },
        },
      },
    };
    const parsed = parseGovernanceRunResult(run);
    expect(parsed).not.toBeNull();
    const steps = deriveDecisionFlow(parsed, "succeeded");
    const intentIdx = steps.findIndex((s) => s.id === "intent");
    const promptIdx = steps.findIndex((s) => s.id === "prompt");
    expect(intentIdx).toBeGreaterThan(promptIdx);
    expect(steps[intentIdx]?.label).toBe("LLM Intent Router");
    expect(steps[intentIdx]?.detail).toContain("release");
  });

  it("formats hold_release distinctly from patch_block_release", () => {
    expect(formatActionLabel("hold_release")).toBe("Hold Release");
    expect(formatActionLabel("patch_block_release")).toBe("Block Release");
    expect(isHoldReleaseAction("hold_release")).toBe(true);
    expect(isHoldReleaseAction("patch_block_release")).toBe(false);
  });

  it("counts tool calls from raw_signals keys", () => {
    const raw = {
      get_ci_status: { ci_pass_rate: 0.9, transport: "mcp" },
      get_deploy_history: { change_fail_rate: 0.1, transport: "direct_api" },
    };
    expect(countToolCallsFromRawSignals(raw, "devops")).toEqual({ used: 2, max: 7 });
    expect(formatToolCallLabel(raw, "devops")).toBe("DevOps 2/7");
  });

  it("detects MCP transport in nested raw_signals", () => {
    const raw = {
      get_ci_status: { ci_pass_rate: 0.9, transport: "mcp" },
    };
    expect(deriveTransportFromRawSignals(raw)).toBe("mcp");
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
