import { CONNECTOR_HELP, CONNECTOR_ORDER, type ConnectorsTabProps } from "./types";

export function ConnectorsTab({
  canEdit,
  saving,
  connectorDraft,
  setConnectorDraft,
  mergeConnectorConfig,
  mergeConnectorCreds,
  connectorStatus,
  onSaveAll,
  onSaveAndTest,
  onValidate,
}: ConnectorsTabProps) {
  return (
    <div className="card settings-connectors-card">
      <div className="workspace-section-intro">
        <div>
          <h2>Connectors</h2>
          <p>
            Use the quick fields for each system, then <strong>Save &amp; test</strong> to store settings and run the connection check in one step. Use{" "}
            <strong>Test only</strong> if you already saved and only want to re-check.
          </p>
        </div>
      </div>
      <p className="field-hint settings-cred-hint">
        Credentials are encrypted when saved and are never returned by the API — re-enter a token or password to update it.
      </p>

      {CONNECTOR_ORDER.map((name) => {
        const draft = connectorDraft[name];
        const status = connectorStatus(name);
        if (!draft) return null;
        const cfg = draft.config_json ?? {};
        const cred = draft.credentials_json ?? {};

        return (
          <div key={name} className="config-block settings-connector-block">
            <div className="settings-connector-head">
              <h3 className="settings-connector-title">{name}</h3>
              <label className="settings-enable-inline">
                <input
                  type="checkbox"
                  checked={draft.enabled}
                  onChange={(e) =>
                    setConnectorDraft((prev) => ({
                      ...prev,
                      [name]: { ...prev[name], enabled: e.target.checked },
                    }))
                  }
                  disabled={!canEdit || saving}
                />{" "}
                Enabled
              </label>
            </div>
            <p className="field-hint">{CONNECTOR_HELP[name] ?? "Configure and test."}</p>

            {name === "github" ? (
              <div className="config-columns settings-quick-grid">
                <div className="form-row">
                  <label>Repository</label>
                  <input
                    value={String(cfg.repo ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { repo: e.target.value })}
                    placeholder="owner/repo"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>GitHub token (PAT)</label>
                  <input
                    type="password"
                    autoComplete="off"
                    value={String(cred.token ?? "")}
                    onChange={(e) => mergeConnectorCreds(name, { token: e.target.value })}
                    placeholder={status?.credentials_keys_configured?.includes("token") ? "Configured (masked)" : "ghp_…"}
                    disabled={!canEdit || saving}
                  />
                </div>
              </div>
            ) : null}

            {name === "gitlab" ? (
              <div className="config-columns settings-quick-grid">
                <div className="form-row">
                  <label>GitLab URL</label>
                  <input
                    value={String(cfg.gitlab_url ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { gitlab_url: e.target.value })}
                    placeholder="https://gitlab.com"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Project ID / Path</label>
                  <input
                    value={String(cfg.project_id ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { project_id: e.target.value })}
                    placeholder="owner/repo or project numeric ID"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Personal access token</label>
                  <input
                    type="password"
                    autoComplete="off"
                    value={String(cred.token ?? "")}
                    onChange={(e) => mergeConnectorCreds(name, { token: e.target.value })}
                    placeholder={status?.credentials_keys_configured?.includes("token") ? "Configured (masked)" : "Enter token"}
                    disabled={!canEdit || saving}
                  />
                </div>
              </div>
            ) : null}

            {name === "bitbucket" ? (
              <div className="config-columns settings-quick-grid">
                <div className="form-row">
                  <label>Workspace</label>
                  <input
                    value={String(cfg.workspace ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { workspace: e.target.value })}
                    placeholder="Workspace ID"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Repository Slug</label>
                  <input
                    value={String(cfg.repo_slug ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { repo_slug: e.target.value })}
                    placeholder="repo-slug"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>App Password</label>
                  <input
                    type="password"
                    autoComplete="off"
                    value={String(cred.app_password ?? "")}
                    onChange={(e) => mergeConnectorCreds(name, { app_password: e.target.value })}
                    placeholder={status?.credentials_keys_configured?.includes("app_password") ? "Configured (masked)" : "Enter app password"}
                    disabled={!canEdit || saving}
                  />
                </div>
              </div>
            ) : null}

            {name === "jira" ? (
              <div className="config-columns settings-quick-grid">
                <div className="form-row">
                  <label>Jira base URL</label>
                  <input
                    value={String(cfg.base_url ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { base_url: e.target.value.replace(/\/$/, "") })}
                    placeholder="https://your-domain.atlassian.net"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Project key</label>
                  <input
                    value={String(cfg.project ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { project: e.target.value.toUpperCase() })}
                    placeholder="PROJ"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Agile board ID</label>
                  <input
                    value={String(cfg.board_id ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { board_id: e.target.value })}
                    placeholder="1"
                    disabled={!canEdit || saving}
                  />
                  <p className="field-hint">Required for PM sprint tools (active sprint, blockers, velocity).</p>
                </div>
                <div className="form-row">
                  <label>Account email</label>
                  <input
                    type="email"
                    value={String(cred.email ?? "")}
                    onChange={(e) => mergeConnectorCreds(name, { email: e.target.value })}
                    placeholder={status?.credentials_keys_configured?.includes("email") ? "Configured (masked)" : "you@company.com"}
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>API token</label>
                  <input
                    type="password"
                    autoComplete="off"
                    value={String(cred.token ?? "")}
                    onChange={(e) => mergeConnectorCreds(name, { token: e.target.value })}
                    placeholder={status?.credentials_keys_configured?.includes("token") ? "Configured (masked)" : "Enter token"}
                    disabled={!canEdit || saving}
                  />
                </div>
              </div>
            ) : null}

            {name === "azure" ? (
              <div className="config-columns settings-quick-grid">
                <div className="form-row">
                  <label>Organization</label>
                  <input
                    value={String(cfg.organization ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { organization: e.target.value })}
                    placeholder="Azure DevOps org name"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Project</label>
                  <input
                    value={String(cfg.project ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { project: e.target.value })}
                    placeholder="Project name"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Repository</label>
                  <input
                    value={String(cfg.repo ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { repo: e.target.value })}
                    placeholder="Repository name (optional)"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Personal access token (PAT)</label>
                  <input
                    type="password"
                    autoComplete="off"
                    value={String(cred.token ?? "")}
                    onChange={(e) => mergeConnectorCreds(name, { token: e.target.value })}
                    placeholder="Build + Release read scopes"
                    disabled={!canEdit || saving}
                  />
                </div>
              </div>
            ) : null}

            {name === "aws" ? (
              <div className="config-columns settings-quick-grid">
                <div className="form-row">
                  <label>AWS account ID</label>
                  <input
                    value={String(cfg.account_id ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { account_id: e.target.value })}
                    placeholder="123456789012"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Region</label>
                  <input
                    value={String(cfg.region ?? "us-east-1")}
                    onChange={(e) => mergeConnectorConfig(name, { region: e.target.value })}
                    placeholder="us-east-1"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Access key ID</label>
                  <input
                    type="password"
                    autoComplete="off"
                    value={String(cred.access_key_id ?? "")}
                    onChange={(e) => mergeConnectorCreds(name, { access_key_id: e.target.value })}
                    placeholder={
                      status?.credentials_keys_configured?.includes("access_key_id") ? "Configured (masked)" : "AKIA…"
                    }
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Secret access key</label>
                  <input
                    type="password"
                    autoComplete="off"
                    value={String(cred.secret_access_key ?? "")}
                    onChange={(e) => mergeConnectorCreds(name, { secret_access_key: e.target.value })}
                    placeholder={
                      status?.credentials_keys_configured?.includes("secret_access_key")
                        ? "Configured (masked)"
                        : "Enter secret key"
                    }
                    disabled={!canEdit || saving}
                  />
                </div>
              </div>
            ) : null}

            {name === "finops" ? (
              <div className="config-columns settings-quick-grid">
                <div className="form-row">
                  <label>Cost file path</label>
                  <input
                    value={String(cfg.cost_file ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { cost_file: e.target.value })}
                    placeholder="/path/to/cost-export.json"
                    disabled={!canEdit || saving}
                  />
                </div>
              </div>
            ) : null}

            {name === "vps" ? (
              <div className="config-columns settings-quick-grid">
                <div className="form-row">
                  <label>Provider</label>
                  <input
                    value={String(cfg.provider ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { provider: e.target.value })}
                    placeholder="Hostinger"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Host</label>
                  <input
                    value={String(cfg.host ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { host: e.target.value })}
                    placeholder="vps.example.com"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Status URL (optional)</label>
                  <input
                    value={String(cfg.status_url ?? "")}
                    onChange={(e) => mergeConnectorConfig(name, { status_url: e.target.value })}
                    placeholder="https://vps.example.com/health"
                    disabled={!canEdit || saving}
                  />
                </div>
                <div className="form-row">
                  <label>Bearer token (optional)</label>
                  <input
                    type="password"
                    autoComplete="off"
                    value={String(cred.token ?? "")}
                    onChange={(e) => mergeConnectorCreds(name, { token: e.target.value })}
                    placeholder="Token for status URL"
                    disabled={!canEdit || saving}
                  />
                </div>
              </div>
            ) : null}

            <div className="actions settings-connector-actions">
              <span
                className={`status-chip ${
                  status?.last_validation_ok === true
                    ? "succeeded"
                    : status?.last_validation_ok === false
                      ? "failed"
                      : "queued"
                }`}
              >
                {status?.last_validation_ok === true
                  ? "Check OK"
                  : status?.last_validation_ok === false
                    ? "Check failed"
                    : "Not checked yet"}
              </span>
              <button
                className="btn btn-primary"
                type="button"
                onClick={() => void onSaveAndTest(name)}
                disabled={!canEdit || saving}
              >
                Save &amp; test
              </button>
              <button className="btn btn-ghost" type="button" onClick={() => void onValidate(name)} disabled={!canEdit || saving}>
                Test only
              </button>
              {status?.last_validation_error ? (
                <span className="settings-validation-msg" title={status.last_validation_error}>
                  {status.last_validation_error}
                </span>
              ) : null}
            </div>

            <details className="settings-advanced-details settings-connector-raw">
              <summary>Edit raw JSON</summary>
              <div className="form-row">
                <label>Config JSON</label>
                <textarea
                  className="settings-json-area"
                  value={JSON.stringify(draft.config_json ?? {}, null, 2)}
                  onChange={(e) => {
                    try {
                      const parsed = JSON.parse(e.target.value || "{}") as Record<string, unknown>;
                      setConnectorDraft((prev) => ({ ...prev, [name]: { ...prev[name], config_json: parsed } }));
                    } catch {
                      /* keep editable */
                    }
                  }}
                  disabled={!canEdit || saving}
                  rows={6}
                />
              </div>
              <div className="form-row">
                <label>Credentials JSON</label>
                <textarea
                  className="settings-json-area"
                  value={JSON.stringify(draft.credentials_json ?? {}, null, 2)}
                  onChange={(e) => {
                    try {
                      const parsed = JSON.parse(e.target.value || "{}") as Record<string, unknown>;
                      setConnectorDraft((prev) => ({ ...prev, [name]: { ...prev[name], credentials_json: parsed } }));
                    } catch {
                      /* keep editable */
                    }
                  }}
                  disabled={!canEdit || saving}
                  rows={5}
                />
              </div>
            </details>
          </div>
        );
      })}

      <div className="actions settings-connectors-footer">
        <button className="btn btn-ghost" type="button" disabled={!canEdit || saving} onClick={onSaveAll}>
          {saving ? "Saving…" : "Save all connectors (no test)"}
        </button>
      </div>
    </div>
  );
}
