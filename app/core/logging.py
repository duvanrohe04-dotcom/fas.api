"""Structured logging configuration."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__)


class JsonFormatter(logging.Formatter):
    """Format log records as single line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize the record with its extra context."""
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(
            {key: value for key, value in record.__dict__.items() if key not in _RESERVED}
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human readable console formatter used outside production."""

    def format(self, record: logging.LogRecord) -> str:
        """Render a compact human friendly line."""
        stamp = self.formatTime(record, "%H:%M:%S")
        base = f"{stamp} {record.levelname:<7} {record.name}: {record.getMessage()}"
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _RESERVED and not key.startswith("_") and key not in ("name",)
        }
        if extras:
            base = f"{base} {json.dumps(extras, default=str, ensure_ascii=False)}"
        return base


def setup_logging(level: str | None = None) -> None:
    """Configure the root logger with a single handler."""
    settings = get_settings()
    resolved_level = level or ("INFO" if settings.is_production else "DEBUG")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if settings.is_production else ConsoleFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(resolved_level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
