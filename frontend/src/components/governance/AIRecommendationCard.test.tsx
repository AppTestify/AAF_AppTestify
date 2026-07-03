import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import { AIRecommendationCard } from "./AIRecommendationCard";
import type { RecommendationView } from "../../lib/governancePresentation";

const mockRecommendation: RecommendationView = {
  headline: "Hold Release",
  narrative: "Significant delivery and cost risks detected.",
  consensusScore: 0.82,
  rarTriggered: true,
  utilityScore: 0.75,
  confidenceLabel: "High",
  runId: 101,
  badges: [
    { label: "AI Recommendation", variant: "primary" },
    { label: "Consensus Aligned", variant: "success" },
  ],
};

describe("AIRecommendationCard", () => {
  it("renders correctly with full data", () => {
    render(
      <BrowserRouter>
        <AIRecommendationCard recommendation={mockRecommendation} />
      </BrowserRouter>
    );

    expect(screen.getByText("Hold Release")).toBeInTheDocument();
    expect(screen.getByText("Significant delivery and cost risks detected.")).toBeInTheDocument();
    expect(screen.getByText("CONFIDENCE High")).toBeInTheDocument();
    expect(screen.getByText("AI Recommendation")).toBeInTheDocument();
    expect(screen.getByText("Consensus Aligned")).toBeInTheDocument();

    expect(screen.getByText("0.82")).toBeInTheDocument(); // Consensus
    expect(screen.getByText("Yes")).toBeInTheDocument();  // RAR Triggered
    expect(screen.getByText("0.75")).toBeInTheDocument(); // Utility Score

    expect(screen.getByRole("link", { name: "Review Decision →" })).toHaveAttribute("href", "/app/cases?run_id=101");
    expect(screen.getByRole("link", { name: "View Evidence" })).toHaveAttribute("href", "/app/evidence?run_id=101");
    expect(screen.getByRole("link", { name: "Agent Reasoning" })).toHaveAttribute("href", "/app/runs?run_id=101");
    expect(screen.getByRole("link", { name: "Executive Brief" })).toHaveAttribute("href", "/app/brief?run_id=101");
  });

  it("handles missing runId correctly", () => {
    const noRunRec = { ...mockRecommendation, runId: null };
    render(
      <BrowserRouter>
        <AIRecommendationCard recommendation={noRunRec} />
      </BrowserRouter>
    );

    expect(screen.getByRole("link", { name: "Review Decision →" })).toHaveAttribute("href", "/app/cases");
    expect(screen.getByRole("link", { name: "View Evidence" })).toHaveAttribute("href", "/app/evidence");
    expect(screen.getByRole("link", { name: "Agent Reasoning" })).toHaveAttribute("href", "/app/runs");
    expect(screen.queryByRole("link", { name: "Executive Brief" })).not.toBeInTheDocument();
  });
});
