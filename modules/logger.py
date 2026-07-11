"""
logger.py
=========
Centralized logging configuration for the Linux Server Health Check tool.

Provides a single `get_logger()` factory so every module writes to the
same rotating log file (``logs/application.log``) and to the console,
with a consistent format that includes timestamps, log level, module
name, and message.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from config import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def _configure_root() -> None:
    """Configure the root logger exactly once (idempotent)."""
    global _configured
    if _configured:
        return

    os.makedirs(settings.LOGS_DIR, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a module-scoped logger that writes to the shared rotating log
    file and the console.

    Args:
        name: Usually ``__name__`` of the calling module.

    Returns:
        A configured ``logging.Logger`` instance.
    """
    _configure_root()
    return logging.getLogger(name)
