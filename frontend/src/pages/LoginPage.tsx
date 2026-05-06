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
          <div className="card auth-card-main">
            <div className="auth-badge">Secure Workspace Access</div>
            <h1 className="auth-heading">Sign in</h1>
            <p className="auth-sub">Access governed operations with tenant-scoped controls, decision trails, and executive visibility.</p>
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
          <div className="card auth-card-side">
            <h2>Enterprise Access</h2>
            <p>Built for secure, accountable operations across multiple teams and tenants.</p>
            <div className="auth-kpis">
              <div className="auth-kpi">
                <span className="label">Access model</span>
                <strong>JWT + role-aware</strong>
              </div>
              <div className="auth-kpi">
                <span className="label">Governance</span>
                <strong>Audited workflows</strong>
              </div>
            </div>
            <ul className="auth-points">
              <li>Superadmin and tenant-admin separation</li>
              <li>Approval and decision audit trail</li>
              <li>Operational dashboard visibility</li>
            </ul>
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
