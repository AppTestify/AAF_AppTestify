import { Link } from "react-router-dom";

type MarketingLayoutProps = {
  signupOpen: boolean | null;
  children: React.ReactNode;
};

export function MarketingLayout({ signupOpen, children }: MarketingLayoutProps) {
  return (
    <div className="marketing">
      <header className="site-header">
        <div className="site-header-inner site-nav">
          <Link to="/" className="site-logo">
            <span className="site-logo-mark" aria-hidden="true" />
            <span className="site-logo-text">Casantris</span>
          </Link>
          <nav className="site-nav-links" aria-label="Primary">
            <Link to="/platform">Platform</Link>
            <Link to="/capabilities">Agents & tools</Link>
            <Link to="/how-it-works">How it works</Link>
            <Link to="/enterprise">Enterprise</Link>
          </nav>
          <div className="site-nav-cta">
            <Link to="/platform" className="btn btn-ghost btn-sm">
              Trust architecture
            </Link>
            <Link to="/request-access" className="btn btn-ghost btn-sm">
              Request access
            </Link>
            {signupOpen ? (
              <Link to="/signup" className="btn btn-ghost btn-sm">
                Create organization
              </Link>
            ) : null}
            <Link to="/login" className="btn btn-primary btn-sm">
              Sign in
            </Link>
          </div>
        </div>
      </header>
      {children}
      <footer className="site-footer">
        <div className="site-footer-grid">
          <div className="site-footer-brand">
            <div className="site-footer-name-row">
              <span className="site-logo-mark site-logo-mark--footer" aria-hidden="true" />
              <span className="site-footer-name">Casantris</span>
            </div>
            <p className="site-footer-tagline">
              Four-agent governance — DevOps, PM, FinOps, DevSecOps — with seventeen live tools and audit-ready decisions.
            </p>
          </div>
          <div className="site-footer-col">
            <span className="site-footer-heading">Product</span>
            <Link to="/login">Workspace</Link>
            {signupOpen ? <Link to="/signup">Create organization</Link> : null}
            <Link to="/platform">Platform</Link>
            <Link to="/capabilities">Agents & tools</Link>
          </div>
          <div className="site-footer-col">
            <span className="site-footer-heading">Company</span>
            <Link to="/enterprise">Enterprise</Link>
            <Link to="/how-it-works">How it works</Link>
            <Link to="/request-access">Request access</Link>
          </div>
        </div>
        <div className="site-footer-bottom">
          <span>Patent Application No: 202621008211 | Status: Applied</span>
          <span>Product of AppTestify Global Services Private Limited | CIN: U74999DL2021PTC382674 | © 2026 AppTestify. All rights reserved.</span>
        </div>
      </footer>
    </div>
  );
}
