import type { NotificationTemplate } from "./types";
import type { UsersTabProps } from "./types";

const CHANNEL_EVENTS = [
  { key: "governance_run_complete", label: "Run complete" },
  { key: "governance_run_failed", label: "Run failed" },
  { key: "case_created", label: "Case created" },
  { key: "audit_alert_critical", label: "Critical audit" },
  { key: "report_digest", label: "Report digest" },
] as const;

export function UsersTab({
  canEdit,
  saving,
  adminUsers,
  newUserEmail,
  setNewUserEmail,
  newUserRole,
  setNewUserRole,
  onAddUser,
  notificationCfg,
  setNotificationCfg,
  smtpPassword,
  setSmtpPassword,
  smtpTestEmail,
  setSmtpTestEmail,
  slackWebhook,
  setSlackWebhook,
  clearSlackWebhook,
  setClearSlackWebhook,
  teamsWebhook,
  setTeamsWebhook,
  clearTeamsWebhook,
  setClearTeamsWebhook,
  onTestSmtp,
  onSaveNotifications,
}: UsersTabProps) {
  const updateChannel = (eventKey: string, channel: "email" | "slack" | "teams", value: boolean) => {
    setNotificationCfg((p) => {
      if (!p) return p;
      const current = p.notification_channels[eventKey] ?? { email: true, slack: false, teams: false };
      return {
        ...p,
        notification_channels: {
          ...p.notification_channels,
          [eventKey]: { ...current, [channel]: value },
        },
      };
    });
  };

  return (
    <div className="card">
      <div className="workspace-section-intro">
        <div>
          <h2>Users, SMTP, and notifications</h2>
          <p>Manage RBAC users, SMTP delivery, Slack/Teams webhooks, channel toggles, and digest schedules.</p>
        </div>
      </div>
      <div className="config-block">
        <h3>Tenant users</h3>
        <div className="config-columns">
          <div className="form-row">
            <label>Email</label>
            <input value={newUserEmail} onChange={(e) => setNewUserEmail(e.target.value)} placeholder="user@company.com" />
          </div>
          <div className="form-row">
            <label>Role</label>
            <select value={newUserRole} onChange={(e) => setNewUserRole(e.target.value)}>
              <option value="reviewer">reviewer</option>
              <option value="tenant_admin">tenant_admin</option>
            </select>
          </div>
        </div>
        <div className="actions">
          <button className="btn btn-primary" type="button" onClick={onAddUser} disabled={!canEdit || saving}>
            Add user and send password email
          </button>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Roles</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {adminUsers.map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{u.role_names.join(", ") || "-"}</td>
                  <td>{u.is_active ? "active" : "disabled"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="config-block">
        <h3>SMTP setup</h3>
        {notificationCfg?.using_platform_smtp ? (
          <p className="workspace-meta">
            <span className="badge badge-info">Using platform SMTP</span> Tenant override is optional; platform defaults apply when tenant SMTP is not enabled.
          </p>
        ) : null}
        {!notificationCfg?.using_platform_smtp && notificationCfg?.platform_smtp_configured ? (
          <p className="workspace-meta">Platform SMTP is configured as fallback when tenant delivery is disabled.</p>
        ) : null}
        <div className="config-columns">
          <div className="form-row">
            <label>SMTP host</label>
            <input
              value={notificationCfg?.smtp_host ?? ""}
              onChange={(e) => setNotificationCfg((p) => (p ? { ...p, smtp_host: e.target.value } : p))}
            />
          </div>
          <div className="form-row">
            <label>SMTP port</label>
            <input
              value={notificationCfg?.smtp_port ?? ""}
              onChange={(e) =>
                setNotificationCfg((p) => (p ? { ...p, smtp_port: Number(e.target.value || 0) || null } : p))
              }
            />
          </div>
          <div className="form-row">
            <label>Username</label>
            <input
              value={notificationCfg?.smtp_username ?? ""}
              onChange={(e) => setNotificationCfg((p) => (p ? { ...p, smtp_username: e.target.value } : p))}
            />
          </div>
          <div className="form-row">
            <label>Password</label>
            <input
              type="password"
              value={smtpPassword}
              onChange={(e) => setSmtpPassword(e.target.value)}
              placeholder={notificationCfg?.smtp_password_configured ? "Configured (enter to rotate)" : ""}
            />
          </div>
          <div className="form-row">
            <label>From email</label>
            <input
              value={notificationCfg?.smtp_from_email ?? ""}
              onChange={(e) => setNotificationCfg((p) => (p ? { ...p, smtp_from_email: e.target.value } : p))}
            />
          </div>
          <div className="form-row">
            <label>Test recipient</label>
            <input value={smtpTestEmail} onChange={(e) => setSmtpTestEmail(e.target.value)} placeholder="optional test email" />
          </div>
        </div>
        <div className="form-row">
          <label>
            <input
              type="checkbox"
              checked={notificationCfg?.use_tls ?? true}
              onChange={(e) => setNotificationCfg((p) => (p ? { ...p, use_tls: e.target.checked } : p))}
            />{" "}
            Use TLS
          </label>
          <label>
            <input
              type="checkbox"
              checked={notificationCfg?.use_ssl ?? false}
              onChange={(e) => setNotificationCfg((p) => (p ? { ...p, use_ssl: e.target.checked } : p))}
            />{" "}
            Use SSL
          </label>
          <label>
            <input
              type="checkbox"
              checked={notificationCfg?.notifications_enabled ?? false}
              onChange={(e) => setNotificationCfg((p) => (p ? { ...p, notifications_enabled: e.target.checked } : p))}
            />{" "}
            Enable tenant SMTP override
          </label>
        </div>
        <div className="config-block" style={{ marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--border, #ddd)" }}>
          <h3>Governance run delivery</h3>
          <p className="workspace-meta" style={{ marginTop: 0 }}>
            On successful run completion, notify via enabled channels with a signed public link. Set <code>PUBLIC_SHARE_BASE_URL</code> on the API host for background jobs.
          </p>
          <div className="form-row">
            <label>
              <input
                type="checkbox"
                checked={notificationCfg?.governance_notify_on_run_complete ?? false}
                onChange={(e) =>
                  setNotificationCfg((p) => (p ? { ...p, governance_notify_on_run_complete: e.target.checked } : p))
                }
              />{" "}
              Notify when a governance run completes
            </label>
          </div>
          <div className="form-row">
            <label>Slack incoming webhook URL</label>
            <input
              type="url"
              value={slackWebhook}
              onChange={(e) => setSlackWebhook(e.target.value)}
              placeholder={
                notificationCfg?.slack_webhook_configured ? "Configured (enter a new URL to rotate)" : "https://hooks.slack.com/services/…"
              }
            />
            <label style={{ marginTop: "0.35rem", display: "block" }}>
              <input type="checkbox" checked={clearSlackWebhook} onChange={(e) => setClearSlackWebhook(e.target.checked)} /> Remove stored Slack webhook
            </label>
          </div>
          <div className="form-row">
            <label>Microsoft Teams incoming webhook URL</label>
            <input
              type="url"
              value={teamsWebhook}
              onChange={(e) => setTeamsWebhook(e.target.value)}
              placeholder={
                notificationCfg?.teams_webhook_configured
                  ? "Configured (enter a new URL to rotate)"
                  : "https://outlook.office.com/webhook/…"
              }
            />
            <label style={{ marginTop: "0.35rem", display: "block" }}>
              <input type="checkbox" checked={clearTeamsWebhook} onChange={(e) => setClearTeamsWebhook(e.target.checked)} /> Remove stored Teams webhook
            </label>
          </div>
          <div className="form-row">
            <label>Digest emails (comma or newline separated)</label>
            <textarea
              rows={3}
              value={(notificationCfg?.governance_run_notify_emails ?? []).join("\n")}
              onChange={(e) =>
                setNotificationCfg((p) =>
                  p
                    ? {
                        ...p,
                        governance_run_notify_emails: e.target.value
                          .split(/[\n,]+/)
                          .map((s) => s.trim())
                          .filter(Boolean),
                      }
                    : p
                )
              }
              placeholder="ops@example.com"
            />
          </div>
        </div>
        <div className="config-block" style={{ marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--border, #ddd)" }}>
          <h3>Notification channels</h3>
          <p className="workspace-meta">Choose email, Slack, and Teams delivery per event type.</p>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Email</th>
                  <th>Slack</th>
                  <th>Teams</th>
                </tr>
              </thead>
              <tbody>
                {CHANNEL_EVENTS.map(({ key, label }) => {
                  const ch = notificationCfg?.notification_channels[key] ?? { email: true, slack: false, teams: false };
                  return (
                    <tr key={key}>
                      <td>{label}</td>
                      <td>
                        <input type="checkbox" checked={ch.email} onChange={(e) => updateChannel(key, "email", e.target.checked)} disabled={!canEdit} />
                      </td>
                      <td>
                        <input type="checkbox" checked={ch.slack} onChange={(e) => updateChannel(key, "slack", e.target.checked)} disabled={!canEdit} />
                      </td>
                      <td>
                        <input type="checkbox" checked={ch.teams} onChange={(e) => updateChannel(key, "teams", e.target.checked)} disabled={!canEdit} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
        <div className="config-block" style={{ marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--border, #ddd)" }}>
          <h3>Scheduled report digests</h3>
          <div className="form-row">
            <label>
              <input
                type="checkbox"
                checked={notificationCfg?.digest_schedule.daily_enabled ?? false}
                onChange={(e) =>
                  setNotificationCfg((p) =>
                    p ? { ...p, digest_schedule: { ...p.digest_schedule, daily_enabled: e.target.checked } } : p
                  )
                }
              />{" "}
              Daily digest (UTC)
            </label>
            <input
              type="time"
              value={notificationCfg?.digest_schedule.daily_time_utc ?? "08:00"}
              onChange={(e) =>
                setNotificationCfg((p) =>
                  p ? { ...p, digest_schedule: { ...p.digest_schedule, daily_time_utc: e.target.value } } : p
                )
              }
            />
          </div>
          <div className="form-row">
            <label>
              <input
                type="checkbox"
                checked={notificationCfg?.digest_schedule.weekly_enabled ?? false}
                onChange={(e) =>
                  setNotificationCfg((p) =>
                    p ? { ...p, digest_schedule: { ...p.digest_schedule, weekly_enabled: e.target.checked } } : p
                  )
                }
              />{" "}
              Weekly digest
            </label>
            <select
              value={notificationCfg?.digest_schedule.weekly_day ?? "monday"}
              onChange={(e) =>
                setNotificationCfg((p) =>
                  p ? { ...p, digest_schedule: { ...p.digest_schedule, weekly_day: e.target.value } } : p
                )
              }
            >
              {["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
            <input
              type="time"
              value={notificationCfg?.digest_schedule.weekly_time_utc ?? "08:00"}
              onChange={(e) =>
                setNotificationCfg((p) =>
                  p ? { ...p, digest_schedule: { ...p.digest_schedule, weekly_time_utc: e.target.value } } : p
                )
              }
            />
          </div>
          <div className="form-row">
            <label>Digest recipients</label>
            <textarea
              rows={2}
              value={(notificationCfg?.digest_schedule.recipients ?? []).join("\n")}
              onChange={(e) =>
                setNotificationCfg((p) =>
                  p
                    ? {
                        ...p,
                        digest_schedule: {
                          ...p.digest_schedule,
                          recipients: e.target.value
                            .split(/[\n,]+/)
                            .map((s) => s.trim())
                            .filter(Boolean),
                        },
                      }
                    : p
                )
              }
              placeholder="digest@example.com"
            />
          </div>
        </div>
        <div className="actions">
          <button className="btn btn-ghost" type="button" onClick={onTestSmtp} disabled={!canEdit || saving}>
            Test SMTP connection
          </button>
          <button className="btn btn-primary" type="button" onClick={onSaveNotifications} disabled={!canEdit || saving}>
            Save SMTP + notifications
          </button>
        </div>
      </div>
      <div className="config-block">
        <h3>Email templates</h3>
        {Object.entries(notificationCfg?.templates ?? {}).map(([key, tpl]) => (
          <div key={key} className="form-row">
            <label>{key} subject</label>
            <input
              value={tpl.subject}
              onChange={(e) =>
                setNotificationCfg((p) =>
                  p
                    ? { ...p, templates: { ...p.templates, [key]: { ...(p.templates[key] as NotificationTemplate), subject: e.target.value } } }
                    : p
                )
              }
            />
            <label>{key} body</label>
            <textarea
              value={tpl.body}
              onChange={(e) =>
                setNotificationCfg((p) =>
                  p ? { ...p, templates: { ...p.templates, [key]: { ...(p.templates[key] as NotificationTemplate), body: e.target.value } } } : p
                )
              }
            />
          </div>
        ))}
      </div>
    </div>
  );
}
