import type { ReactNode } from "react";

type SectionCardProps = {
  title: string;
  description?: string;
  meta?: ReactNode;
  actions?: ReactNode;
  className?: string;
  children: ReactNode;
};

export function SectionCard({
  title,
  description,
  meta,
  actions,
  className = "",
  children,
}: SectionCardProps) {
  return (
    <div className={`card ${className}`.trim()}>
      <div className="workspace-section-intro">
        <div>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {meta ? <div className="workspace-meta">{meta}</div> : null}
        {actions}
      </div>
      {children}
    </div>
  );
}
