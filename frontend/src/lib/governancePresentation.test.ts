import { describe, expect, it } from "vitest";
import { deriveDecisionFlow, isLiveTrace } from "./governancePresentation";

describe("governancePresentation", () => {
  it("marks live trace when run is running", () => {
    expect(isLiveTrace("running", null)).toBe(true);
    expect(isLiveTrace("succeeded", new Date().toISOString())).toBe(true);
  });

  it("returns default flow without parsed run", () => {
    const steps = deriveDecisionFlow(null);
    expect(steps.length).toBeGreaterThan(4);
  });
});
