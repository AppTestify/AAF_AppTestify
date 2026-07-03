"""Post-run notifications — delegates to notification_router."""

from __future__ import annotations

from app.services.notification_router import deliver_run_complete


def deliver_run_complete_notifications(run_id: int) -> None:
    """Best-effort delivery after a successful governance run (own DB session)."""
    deliver_run_complete(run_id)
