import type { ReactNode } from "react";

type WorkspacePageShellProps = {
  variant: "governance" | "operational";
  title: string;
  subtitle?: string;
  /** Governance variant eyebrow label (e.g. "Command Center"). */
  eyebrow?: string;
  /** Full-width dashboard layout (Command Center). */
  dashboard?: boolean;
  className?: string;
  children: ReactNode;
};

export function WorkspacePageShell({
  variant,
  title,
  subtitle,
  eyebrow,
  dashboard = false,
  className = "",
  children,
}: WorkspacePageShellProps) {
  const pageClass = ["workspace-page", dashboard ? "workspace-page--dashboard" : "", className]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={pageClass}>
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      {variant === "governance" ? (
        <header className="gov-hub-header">
          {eyebrow ? <p className="gov-hub-eyebrow">{eyebrow}</p> : null}
          <h1 className="gov-hub-title">{title}</h1>
          {subtitle ? <p className="gov-hub-lead">{subtitle}</p> : null}
        </header>
      ) : (
        <header className="app-header workspace-page-head">
          <div className="brand">
            <h1>{title}</h1>
            {subtitle ? <span>{subtitle}</span> : null}
          </div>
        </header>
      )}
      <main id="main-content" tabIndex={-1} style={{ outline: "none" }}>
        {children}
      </main>
    </div>
  );
}
