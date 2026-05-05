import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchSignupStatus, signupTenant, type LoginResponse } from "../api";
import "../App.css";

type SignupPageProps = {
  onAuthed: (data: LoginResponse) => void;
};

export function SignupPage({ onAuthed }: SignupPageProps) {
  const navigate = useNavigate();
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [orgName, setOrgName] = useState("");
  const [slug, setSlug] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSignupStatus()
      .then((s) => setEnabled(s.tenant_signup_enabled))
      .catch(() => setEnabled(false));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!enabled) return;
    setError(null);
    setLoading(true);
    try {
      const data = await signupTenant({
        organization_name: orgName.trim(),
        tenant_slug: slug.trim(),
        admin_email: email.trim(),
        password,
      });
      onAuthed(data);
      navigate("/app", { replace: true });
      setPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
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
            <span className="site-logo-text">AgileOps</span>
          </Link>
          <nav className="site-nav-links">
            <Link to="/">Home</Link>
            <Link to="/login">Sign in</Link>
          </nav>
        </div>
      </header>

      <div className="auth-panel">
        <h1 className="auth-heading">Create your organization</h1>
        <p className="auth-sub">You will be the tenant administrator for this workspace.</p>

        {enabled === false ? (
          <div className="alert alert-error" role="alert">
            Self-service signup is disabled on this server. Ask your platform owner for an account, or sign in if you already
            have one.
          </div>
        ) : null}

        {error ? (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        ) : null}

        <div className="card" style={{ maxWidth: 440 }}>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <label htmlFor="org">Organization name</label>
              <input
                id="org"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                placeholder="Acme Delivery"
                required
                disabled={enabled !== true || loading}
              />
            </div>
            <div className="form-row">
              <label htmlFor="slug">URL slug</label>
              <input
                id="slug"
                className="mono"
                value={slug}
                onChange={(e) => setSlug(e.target.value.toLowerCase())}
                placeholder="acme-delivery"
                required
                disabled={enabled !== true || loading}
              />
              <span className="field-hint">Lowercase letters, numbers, and hyphens; must start with a letter.</span>
            </div>
            <div className="form-row">
              <label htmlFor="admin-email">Your admin email</label>
              <input
                id="admin-email"
                type="text"
                inputMode="email"
                autoComplete="email"
                spellCheck={false}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={enabled !== true || loading}
              />
            </div>
            <div className="form-row">
              <label htmlFor="pw">Password</label>
              <input
                id="pw"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={8}
                required
                disabled={enabled !== true || loading}
              />
              <span className="field-hint">At least 8 characters.</span>
            </div>
            <button className="btn btn-primary" type="submit" disabled={loading || enabled !== true}>
              {loading ? "Creating…" : "Create organization"}
            </button>
          </form>
        </div>

        <p className="auth-switch">
          Already have access? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
