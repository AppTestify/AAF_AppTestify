import { useEffect, useState } from "react";
import {
  fetchPlatformNotificationConfig,
  savePlatformNotificationConfig,
  testPlatformNotificationConfig,
  type PlatformNotificationConfig,
} from "../api";
import { WorkspacePageShell } from "../components/layout/WorkspacePageShell";
import { SectionCard } from "../components/ui/SectionCard";

export function WorkspacePlatformSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [cfg, setCfg] = useState<PlatformNotificationConfig | null>(null);
  const [smtpPassword, setSmtpPassword] = useState("");
  const [testEmail, setTestEmail] = useState("");

  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("");
  const [smtpUsername, setSmtpUsername] = useState("");
  const [smtpFromEmail, setSmtpFromEmail] = useState("");
  const [smtpFromName, setSmtpFromName] = useState("");
  const [useTls, setUseTls] = useState(true);
  const [useSsl, setUseSsl] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchPlatformNotificationConfig()
      .then((data) => {
        setCfg(data);
        setSmtpHost(data.smtp_host ?? "");
        setSmtpPort(data.smtp_port != null ? String(data.smtp_port) : "");
        setSmtpUsername(data.smtp_username ?? "");
        setSmtpFromEmail(data.smtp_from_email ?? "");
        setSmtpFromName(data.smtp_from_name ?? "");
        setUseTls(data.use_tls);
        setUseSsl(data.use_ssl);
        setNotificationsEnabled(data.notifications_enabled);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load platform settings"))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await savePlatformNotificationConfig({
        smtp_host: smtpHost.trim() || null,
        smtp_port: smtpPort.trim() ? Number(smtpPort) : null,
        smtp_username: smtpUsername.trim() || null,
        smtp_password: smtpPassword.trim() || undefined,
        smtp_from_email: smtpFromEmail.trim() || null,
        smtp_from_name: smtpFromName.trim() || null,
        use_tls: useTls,
        use_ssl: useSsl,
        notifications_enabled: notificationsEnabled,
      });
      setCfg(updated);
      setSmtpPassword("");
      setMessage("Platform notification settings saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setError(null);
    setMessage(null);
    try {
      const result = await testPlatformNotificationConfig({
        to_email: testEmail.trim() || null,
      });
      setMessage(result.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "SMTP test failed");
    }
  };

  const templateCount = cfg ? Object.keys(cfg.templates).length : 0;

  return (
    <WorkspacePageShell
      variant="operational"
      title="Platform settings"
      subtitle="Platform-wide SMTP defaults and notification templates (superadmin)"
    >
      {loading ? <div className="card">Loading platform settings…</div> : null}
      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}
      {message ? <div className="alert alert-success">{message}</div> : null}

      {!loading ? (
        <div className="card-group">
          <SectionCard
            title="Default SMTP"
            description="Tenants inherit these settings when they have not configured their own SMTP relay."
          >
            <div className="form-grid">
              <div className="form-row">
                <label htmlFor="platform-smtp-host">SMTP host</label>
                <input
                  id="platform-smtp-host"
                  value={smtpHost}
                  onChange={(e) => setSmtpHost(e.target.value)}
                  placeholder="smtp.example.com"
                />
              </div>
              <div className="form-row">
                <label htmlFor="platform-smtp-port">SMTP port</label>
                <input
                  id="platform-smtp-port"
                  value={smtpPort}
                  onChange={(e) => setSmtpPort(e.target.value)}
                  placeholder="587"
                />
              </div>
              <div className="form-row">
                <label htmlFor="platform-smtp-user">Username</label>
                <input
                  id="platform-smtp-user"
                  value={smtpUsername}
                  onChange={(e) => setSmtpUsername(e.target.value)}
                />
              </div>
              <div className="form-row">
                <label htmlFor="platform-smtp-pass">Password</label>
                <input
                  id="platform-smtp-pass"
                  type="password"
                  value={smtpPassword}
                  onChange={(e) => setSmtpPassword(e.target.value)}
                  placeholder={cfg?.smtp_password_configured ? "••••••••" : ""}
                />
              </div>
              <div className="form-row">
                <label htmlFor="platform-from-email">From email</label>
                <input
                  id="platform-from-email"
                  value={smtpFromEmail}
                  onChange={(e) => setSmtpFromEmail(e.target.value)}
                />
              </div>
              <div className="form-row">
                <label htmlFor="platform-from-name">From name</label>
                <input
                  id="platform-from-name"
                  value={smtpFromName}
                  onChange={(e) => setSmtpFromName(e.target.value)}
                />
              </div>
            </div>
            <div className="form-row checkbox-row">
              <label>
                <input type="checkbox" checked={useTls} onChange={(e) => setUseTls(e.target.checked)} />
                Use TLS
              </label>
              <label>
                <input type="checkbox" checked={useSsl} onChange={(e) => setUseSsl(e.target.checked)} />
                Use SSL
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={notificationsEnabled}
                  onChange={(e) => setNotificationsEnabled(e.target.checked)}
                />
                Notifications enabled
              </label>
            </div>
            <div className="actions">
              <button className="btn btn-primary" type="button" onClick={handleSave} disabled={saving}>
                {saving ? "Saving…" : "Save settings"}
              </button>
            </div>
          </SectionCard>

          <SectionCard
            title="SMTP test"
            description="Verify platform relay connectivity and optionally send a welcome template."
          >
            <div className="form-row">
              <label htmlFor="platform-test-email">Test recipient</label>
              <input
                id="platform-test-email"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
                placeholder="admin@example.com"
              />
            </div>
            <div className="actions">
              <button className="btn btn-secondary" type="button" onClick={handleTest}>
                Run SMTP test
              </button>
            </div>
            {cfg?.last_tested_at ? (
              <p className="muted-text">
                Last test: {new Date(cfg.last_tested_at).toLocaleString()} —{" "}
                {cfg.last_test_ok ? "OK" : cfg.last_test_error ?? "failed"}
              </p>
            ) : null}
          </SectionCard>

          <SectionCard
            title="Email templates"
            description={`${templateCount} platform templates ship with body_text and body_html variants.`}
          >
            {cfg ? (
              <details className="accordion">
                <summary>View template keys</summary>
                <ul>
                  {Object.keys(cfg.templates).map((key) => (
                    <li key={key}>
                      <code>{key}</code> — {cfg.templates[key].subject}
                    </li>
                  ))}
                </ul>
              </details>
            ) : null}
          </SectionCard>
        </div>
      ) : null}
    </WorkspacePageShell>
  );
}
