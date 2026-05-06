import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login, type LoginResponse } from "../api";
import "../App.css";

type LoginPageProps = {
  onAuthed: (data: LoginResponse) => void;
  signupEnabled: boolean | null;
};

export function LoginPage({ onAuthed, signupEnabled }: LoginPageProps) {
  const navigate = useNavigate();
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await login(loginEmail.trim(), loginPassword);
      onAuthed(data);
      navigate("/app", { replace: true });
      setLoginPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="marketing auth-page">
      <header className="site-header">
        <div className="site-header-inner site-nav">
          <Link to="/" className="site-logo">
            <span className="site-logo-mark" aria-hidden="true" />
            <span className="site-logo-text">Casantris</span>
          </Link>
          <nav className="site-nav-links">
            <Link to="/">Home</Link>
            {signupEnabled ? <Link to="/signup">Create organization</Link> : null}
          </nav>
        </div>
      </header>

      <div className="auth-panel">
        <div className="auth-surface">
          <div className="auth-layout-stack">
            <div className="card auth-card-main">
              <div className="auth-badge">Trusted Enterprise Access</div>
              <h1 className="auth-heading">Sign in to Casantris</h1>
              <p className="auth-sub">Access governance operations with tenant-scoped controls, policy traceability, and leadership-ready visibility.</p>
              {error ? (
                <div className="alert alert-error" role="alert">
                  {error}
                </div>
              ) : null}
              <form onSubmit={handleLogin}>
                <div className="form-row">
                  <label htmlFor="email">Email</label>
                  <input
                    id="email"
                    type="text"
                    inputMode="email"
                    autoComplete="username"
                    spellCheck={false}
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="form-row">
                  <label htmlFor="password">Password</label>
                  <input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    required
                  />
                </div>
                <button className="btn btn-primary" type="submit" disabled={loading}>
                  {loading ? "Signing in…" : "Sign in"}
                </button>
              </form>
            </div>
          </div>
          <div className="auth-visual-panel" aria-hidden="true">
            <span className="auth-visual-tag">Casantris trust layer</span>
            <h2 className="auth-visual-title">Governance confidence by design</h2>
            <p className="auth-visual-sub">A controlled operating surface that keeps decisions explainable, auditable, and leadership-ready.</p>
            <div className="auth-pillars">
              <div className="auth-pillar">
                <strong>Policy-grade access</strong>
                <span>Role-constrained workflows across superadmin and tenant boundaries.</span>
              </div>
              <div className="auth-pillar">
                <strong>Decision traceability</strong>
                <span>Evidence-linked recommendations and approval history for every critical action.</span>
              </div>
              <div className="auth-pillar">
                <strong>Operational assurance</strong>
                <span>Dashboard posture, telemetry, and exports aligned to enterprise review standards.</span>
              </div>
            </div>
          </div>
        </div>
        {signupEnabled ? (
          <p className="auth-switch">
            New team? <Link to="/signup">Create your organization</Link>
          </p>
        ) : null}
        <div className="auth-footer">
          Product of AppTestify Global Services Private Limited | CIN: U74999DL2021PTC382674 | © 2026 AppTestify. All rights reserved.
        </div>
      </div>
    </div>
  );
}
