# Actionable Automation Runbook

## Enable automation

1. Tenant admin → **Settings** → patch `ui_preferences.action_automation`:
   ```json
   {
     "enabled": true,
     "dry_run": false,
     "jira_blocker_enabled": true,
     "hold_release_workflow_enabled": true,
     "hold_release_webhook_url": "https://your-ci.example.com/hooks/hold-release"
   }
   ```
2. Configure Jira connector (base URL, email, API token, project key).

## Execution paths

| Trigger | When |
|---------|------|
| Decision approval | `POST /decisions/{id}/approve` with `hold_release` when `enabled` |
| Manual | **Execute decision** on Runs page or `POST /runs/{id}/execute-actions` |

## Verify

```bash
# List actions for a decision
curl -b cookies.txt https://api.example.com/api/v1/governance/decisions/42/actions

# Dry-run first
# Set action_automation.dry_run=true — actions state=simulated, no Jira POST
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No actions created | Check `action_automation.enabled` and action is `hold_release` |
| Jira `failed` | Validate connector credentials and project key |
| Webhook ignored | URL must be https in production; check `hold_release_webhook_url` |
