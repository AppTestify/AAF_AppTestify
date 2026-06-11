"""Structured logging with request/tenant context."""

from __future__ import annotations

import logging
import sys

try:
    import structlog

    def configure_structlog() -> None:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        )
        logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)

except ImportError:

    def configure_structlog() -> None:
        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            stream=sys.stdout,
            level=logging.INFO,
        )
