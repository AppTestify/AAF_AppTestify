import type { FlowStep } from "../../lib/governancePresentation";

type DecisionFlowTraceProps = {
  steps: FlowStep[];
  live?: boolean;
};

export function DecisionFlowTrace({ steps, live }: DecisionFlowTraceProps) {
  return (
    <section className="gov-decision-flow-section">
      <div className="gov-decision-flow-head">
        <div>
          <h3>Decision Flow</h3>
          <p>How Casantris arrived at this recommendation</p>
        </div>
        {live ? <span className="gov-live-badge">Live trace</span> : null}
      </div>
      <div className="gov-decision-flow">
        {steps.map((step, i) => (
          <div key={step.id} className="gov-flow-step-wrap">
            <div className={`gov-flow-step ${step.active ? "gov-flow-step--active" : ""}`}>
              <span className="gov-flow-step-label">{step.label}</span>
              {step.detail ? <span className="gov-flow-step-detail">{step.detail}</span> : null}
            </div>
            {i < steps.length - 1 ? <span className="gov-flow-arrow" aria-hidden="true">→</span> : null}
          </div>
        ))}
      </div>
    </section>
  );
}
