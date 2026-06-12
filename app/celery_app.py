"""Celery application for async governance runs."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from aaf.config import get_settings

settings = get_settings()
broker = settings.celery_broker_url or settings.redis_url or "redis://localhost:6379/1"
backend = settings.celery_result_backend or broker

celery_app = Celery("aaf_governance", broker=broker, backend=backend)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=30,
    task_max_retries=2,
    beat_schedule={
        "report-digest-daily": {
            "task": "reports.send_daily_digests",
            "schedule": crontab(minute="*"),
        },
        "report-digest-weekly": {
            "task": "reports.send_weekly_digests",
            "schedule": crontab(minute="*"),
        },
    },
)


@celery_app.task(name="governance.process_run", bind=True)
def process_run_task(self, run_id: int) -> str:
    from app.services.run_jobs import process_run_sync

    try:
        process_run_sync(run_id)
        return f"ok:{run_id}"
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(name="reports.send_daily_digests")
def send_daily_digests_task() -> str:
    from app.tasks.report_digests import send_scheduled_digests

    count = send_scheduled_digests("daily")
    return f"daily:{count}"


@celery_app.task(name="reports.send_weekly_digests")
def send_weekly_digests_task() -> str:
    from app.tasks.report_digests import send_scheduled_digests

    count = send_scheduled_digests("weekly")
    return f"weekly:{count}"
