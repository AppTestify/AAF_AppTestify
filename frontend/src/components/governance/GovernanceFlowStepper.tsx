import { Link } from "react-router-dom";

export type FlowStepLink = {
  id: string;
  label: string;
  route: string;
  active?: boolean;
  completed?: boolean;
};

type GovernanceFlowStepperProps = {
  runId: number;
  activeStep?: string;
};

export function GovernanceFlowStepper({ runId, activeStep = "runs" }: GovernanceFlowStepperProps) {
  const q = `?run_id=${runId}`;
  const steps: FlowStepLink[] = [
    { id: "prompt", label: "Prompt", route: "/app/overview", completed: true },
    { id: "evidence", label: "Evidence", route: `/app/evidence${q}`, active: activeStep === "evidence", completed: activeStep !== "evidence" },
    { id: "runs", label: "Agents", route: `/app/runs${q}`, active: activeStep === "runs", completed: activeStep !== "runs" },
    { id: "cases", label: "Decision", route: `/app/cases${q}`, active: activeStep === "cases" },
    { id: "brief", label: "Brief", route: `/app/brief${q}`, active: activeStep === "brief" },
  ];

  return (
    <nav className="gov-flow-stepper" aria-label="Governance flow">
      {steps.map((step, idx) => (
        <span key={step.id} className="gov-flow-step-wrap">
          <Link
            to={step.route}
            className={`gov-flow-step ${step.active ? "gov-flow-step--active" : ""} ${step.completed ? "gov-flow-step--done" : ""}`}
          >
            <span className="gov-flow-step-num">{idx + 1}</span>
            {step.label}
          </Link>
          {idx < steps.length - 1 ? <span className="gov-flow-step-sep" aria-hidden="true" /> : null}
        </span>
      ))}
    </nav>
  );
}
