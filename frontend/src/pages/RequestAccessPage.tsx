import { useState } from "react";
import { Link } from "react-router-dom";
import { submitRequestAccessLead } from "../api";
import "../App.css";

export function RequestAccessPage() {
  const [organizationName, setOrganizationName] = useState("");
  const [contactName, setContactName] = useState("");
  const [workEmail, setWorkEmail] = useState("");
  const [website, setWebsite] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await submitRequestAccessLead({
        organization_name: organizationName.trim(),
        contact_name: contactName.trim(),
        work_email: workEmail.trim(),
        website: website.trim(),
        notes: notes.trim(),
      });
      setSubmitted(true);
      setOrganizationName("");
      setContactName("");
      setWorkEmail("");
      setWebsite("");
      setNotes("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit request");
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
            <Link to="/login">Sign in</Link>
          </nav>
        </div>
      </header>
      <div className="auth-panel">
        <div className="auth-surface">
          <div className="auth-layout-stack">
            <div className="card auth-card-main">
              <div className="auth-badge">Enterprise Onboarding Intake</div>
              <h1 className="auth-heading">Request access</h1>
              <p className="auth-sub">Submit your details to initiate tenant provisioning, governance scoping, and enterprise readiness review.</p>
              {submitted ? <div className="alert alert-success">Request submitted successfully. We will contact you soon.</div> : null}
              {error ? (
                <div className="alert alert-error" role="alert">
                  {error}
                </div>
              ) : null}
              <form onSubmit={onSubmit}>
                <div className="form-row">
                  <label htmlFor="org-name">Organization name</label>
                  <input id="org-name" value={organizationName} onChange={(e) => setOrganizationName(e.target.value)} required />
                </div>
                <div className="form-row">
                  <label htmlFor="contact-name">Contact name</label>
                  <input id="contact-name" value={contactName} onChange={(e) => setContactName(e.target.value)} required />
                </div>
                <div className="form-row">
                  <label htmlFor="work-email">Work email</label>
                  <input id="work-email" type="email" value={workEmail} onChange={(e) => setWorkEmail(e.target.value)} required />
                </div>
                <div className="form-row">
                  <label htmlFor="website">Website</label>
                  <input id="website" value={website} onChange={(e) => setWebsite(e.target.value)} placeholder="https://example.com" />
                </div>
                <div className="form-row">
                  <label htmlFor="notes">Notes</label>
                  <textarea id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
                </div>
                <button className="btn btn-primary" type="submit" disabled={loading}>
                  {loading ? "Submitting..." : "Submit request"}
                </button>
              </form>
            </div>
          </div>
          <div className="auth-visual-panel" aria-hidden="true">
            <span className="auth-visual-tag">Onboarding assurance</span>
            <h2 className="auth-visual-title">Structured enterprise intake</h2>
            <p className="auth-visual-sub">Designed for platform owners who need controlled onboarding, governance boundaries, and accountable rollout.</p>
            <div className="auth-pillars">
              <div className="auth-pillar">
                <strong>Intake governance</strong>
                <span>Every request flows into a tracked review path before tenant provisioning.</span>
              </div>
              <div className="auth-pillar">
                <strong>Provisioning controls</strong>
                <span>Tenant setup inherits governance-ready defaults for operations and policy.</span>
              </div>
              <div className="auth-pillar">
                <strong>Operational readiness</strong>
                <span>Teams start with role-aware access and traceable governance workflows.</span>
              </div>
            </div>
          </div>
        </div>
        <div className="auth-footer">
          Product of AppTestify Global Services Private Limited | CIN: U74999DL2021PTC382674 | © 2026 AppTestify. All rights reserved.
        </div>
      </div>
    </div>
  );
}
