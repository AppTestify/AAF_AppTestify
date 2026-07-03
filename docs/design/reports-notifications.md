# Reports, notifications, and platform email (CAS-163 R3/R4)

## Overview

Tenant and platform notification delivery supports email (SMTP), Slack (Block Kit), and Microsoft Teams (MessageCard). Report exports can be emailed on demand or via scheduled digests.

## SMTP resolution

1. If tenant SMTP is configured and `notifications_enabled`, use tenant settings.
2. Otherwise fall back to platform SMTP from `PlatformNotificationConfig` (superadmin `/platform/notifications`).

The tenant settings UI shows a **Using platform SMTP** badge when the effective source is platform.

## Notification router

`app/services/notification_router.py` delivers unified notifications for:

| Event | Channels (defaults) |
|-------|---------------------|
| `governance_run_complete` | email, slack, teams |
| `governance_run_failed` | email, slack |
| `case_created` | email |
| `audit_alert_critical` | email, slack, teams |
| `report_digest` | email |

Per-event channel toggles are stored in `TenantNotificationConfig.notification_channels_json`.

## Webhooks

- **Slack:** `app/services/slack_notifier.py` — Block Kit sections + optional action button
- **Teams:** `app/services/teams_notifier.py` — MessageCard with facts and open-uri action

Tenant webhooks override platform defaults when set.

## On-demand report email

`POST /api/v1/reports/email`

```json
{
  "report_type": "runs_summary",
  "format": "xlsx",
  "recipients": ["ops@example.com"],
  "status": "succeeded",
  "limit": 200
}
```

Supported `report_type`: `runs_summary`, `audit_events`, `portfolio_executive`.  
Supported `format`: `xlsx`, `pdf`.

## Scheduled digests

`TenantNotificationConfig.digest_schedule_json`:

```json
{
  "daily_enabled": true,
  "daily_time_utc": "08:00",
  "weekly_enabled": false,
  "weekly_day": "monday",
  "weekly_time_utc": "08:00",
  "recipients": ["ops@example.com"]
}
```

Celery beat tasks (`reports.send_daily_digests`, `reports.send_weekly_digests`) run every minute and match tenant schedules to the current UTC hour/minute.

## Frontend

- **Settings → Users & Notifications:** Teams webhook, per-event channel toggles, digest schedule, platform SMTP badge
- **Reports → Exports:** Email report modal (recipients, format, report type)
