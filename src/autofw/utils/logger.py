"""
Logging utilities — configurable, auto-rotating logger backed by loguru.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from loguru import logger as _loguru_logger


class _InterceptHandler(logging.Handler):
    """Redirect standard-library logging to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        level = _loguru_logger.level(record.levelname).name
        frame = record.__dict__.get("co_filename", "")
        _loguru_logger.opt(depth=6, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(
    level: str = "INFO",
    file_path: str = "logs/framework.log",
    fmt: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
) -> None:
    """Configure the global logger.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        file_path: Where to write log files
        fmt: Log message format
    """
    # Remove any default Loguru sinks
    _loguru_logger.remove()

    # Console sink (stderr)
    _loguru_logger.add(
        sys.stderr,
        level=level,
        format=fmt,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # File sink with auto-rotation
    log_dir = Path(file_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    _loguru_logger.add(
        file_path,
        level=level,
        format=fmt,
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        backtrace=True,
        diagnose=True,
    )

    # Capture all stdlib logging
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    _loguru_logger.info("Logging initialized: level=%s, file=%s", level, file_path)


def get_logger(name: str | None = None) -> "_loguru_logger.__class__":
    """Get a Loguru logger, optionally scoped to a name."""
    return _loguru_logger.bind(name=name or __name__)
