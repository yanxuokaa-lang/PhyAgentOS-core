"""Logging setup for the jevmlx CLI.

Library modules only emit records via ``logging.getLogger(__name__)``; configuring
handlers is the entry point's job (``jevmlx.cli.main``) and is never done on import.
"""

from __future__ import annotations

import json
import logging
import sys

# LogRecord attributes that are not user-supplied "extra" fields.
_RESERVED = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


class _JsonFormatter(logging.Formatter):
    """One JSON object per line: ts, level, logger, msg, plus record extras."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        entry.update({k: v for k, v in record.__dict__.items() if k not in _RESERVED})
        return json.dumps(entry, default=str)


def configure(level: int = logging.WARNING, json_mode: bool = False) -> None:
    """Configure the root logger once (CLI entry point only).

    Args:
        level: handler level (WARNING by default, INFO with ``-v``).
        json_mode: emit one JSON object per line instead of plain text.
    """
    handler = logging.StreamHandler(sys.stderr)
    if json_mode:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()  # idempotent: configure replaces, never stacks handlers
    root.addHandler(handler)
    root.setLevel(level)
