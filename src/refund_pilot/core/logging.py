from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger

_LOG_DIR = Path(os.environ.get("LOG_DIR", "/app/logs"))


def configure_logging(level: str = "INFO") -> None:
    """Configure loguru: JSON stdout (Loki) + rotating file sink.

    Call once at app startup. All modules import `logger` from loguru directly.
    """
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(
        sys.stdout,
        level=level,
        serialize=True,  # JSON format — Loki scrapes this
        enqueue=True,  # async-safe: no blocking on log writes
    )
    logger.add(
        str(_LOG_DIR / "{time:YYYY-MM-DD}.log"),
        level=level,
        serialize=True,
        rotation="00:00",  # new file each day
        retention="7 days",
        enqueue=True,
    )


def get_request_logger(**context: Any) -> Any:
    """Return logger bound with request-scoped context fields.

    Usage:
        log = get_request_logger(request_id="abc", conversation_id="xyz")
        log.info("event_name", extra_field="value")
    """
    return logger.bind(**context)
