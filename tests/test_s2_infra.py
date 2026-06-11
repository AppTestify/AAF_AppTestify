from unittest.mock import patch, MagicMock
from app.services.run_jobs import enqueue_run
import sys
sys.modules['celery'] = MagicMock()
import app.celery_app

def test_enqueue_run_uses_celery_when_broker_configured():
    with patch("app.services.run_jobs._use_celery", return_value=True):
        with patch("app.celery_app.process_run_task.delay") as mock_delay:
            enqueue_run(123)
            mock_delay.assert_called_once_with(123)
