import type { ReactNode } from "react";

type EmptyStateProps = {
  children: ReactNode;
  action?: ReactNode;
  className?: string;
};

export function EmptyState({ children, action, className = "" }: EmptyStateProps) {
  return (
    <div className={`empty-state ${className}`.trim()}>
      <div>{children}</div>
      {action ? <div className="empty-state-action">{action}</div> : null}
    </div>
  );
}
