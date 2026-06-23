import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { RiskMetricCard } from "./RiskMetricCard";
import type { RiskCardView } from "../../lib/governancePresentation";

const mockCards: RiskCardView[] = [
  { id: "release", title: "Release Readiness", status: "Ready", detail: "Consensus aligned", variant: "healthy" },
  { id: "delivery", title: "Delivery Risk", status: "High", detail: "Sprint friction", variant: "action" },
  { id: "cost", title: "Cost Risk", status: "Medium", detail: "Trend warrants review", variant: "watch" },
  { id: "governance", title: "Governance Confidence", status: "82%", detail: "Agent agreement", variant: "healthy" },
];

describe("RiskMetricCard", () => {
  it("renders all given cards with correct text and badges", () => {
    render(<RiskMetricCard cards={mockCards} />);

    expect(screen.getByText("Release Readiness")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("Consensus aligned")).toBeInTheDocument();

    expect(screen.getByText("Delivery Risk")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();

    expect(screen.getByText("Cost Risk")).toBeInTheDocument();
    expect(screen.getByText("Medium")).toBeInTheDocument();

    expect(screen.getByText("Governance Confidence")).toBeInTheDocument();
    expect(screen.getByText("82%")).toBeInTheDocument();

    expect(screen.getAllByText("Healthy")).toHaveLength(2); // Release & Governance
    expect(screen.getByText("Action")).toBeInTheDocument(); // Delivery
    expect(screen.getByText("Watch")).toBeInTheDocument();  // Cost
  });
});
