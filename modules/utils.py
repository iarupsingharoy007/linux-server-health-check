"""
utils.py
========
Small, reusable helper functions shared across check modules: safe
command execution wrappers, numeric parsing helpers, and status
classification helpers.
"""

from typing import Optional

from modules.logger import get_logger
from modules.ssh_connector import CommandExecutionError, SSHConnector

logger = get_logger(__name__)


def safe_run(conn: SSHConnector, command: str, default: str = "") -> str:
    """
    Run a command over SSH and return its stdout, swallowing errors and
    returning a default value instead of raising.

    This is used for "best effort" informational commands where a
    failure should be logged but must not abort the whole check.

    Args:
        conn: An active SSHConnector.
        command: The command to run.
        default: Value to return if the command fails.

    Returns:
        The command's stdout, stripped, or ``default`` on failure.
    """
    try:
        stdout, stderr, exit_status = conn.run(command)
        if exit_status != 0:
            logger.debug("Command '%s' returned non-zero (%d): %s", command, exit_status, stderr)
            return default
        return stdout
    except CommandExecutionError as exc:
        logger.warning("safe_run failed for '%s': %s", command, exc)
        return default


def parse_float(value: str, default: float = 0.0) -> float:
    """Safely parse a string into a float, returning `default` on failure."""
    try:
        return float(value.strip().replace("%", ""))
    except (ValueError, AttributeError):
        return default


def parse_int(value: str, default: int = 0) -> int:
    """Safely parse a string into an int, returning `default` on failure."""
    try:
        return int(float(value.strip()))
    except (ValueError, AttributeError):
        return default


def bytes_to_human(num_bytes: float) -> str:
    """Convert a byte count into a human-readable string (KB, MB, GB, TB)."""
    step = 1024.0
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(num_bytes) < step:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= step
    return f"{num_bytes:.1f} EB"


def classify(value: float, warning: float, critical: float, higher_is_worse: bool = True) -> str:
    """
    Classify a numeric value into 'healthy', 'warning', or 'critical'
    based on threshold values.

    Args:
        value: The measured value (e.g. 82.5 for 82.5% disk usage).
        warning: The warning threshold.
        critical: The critical threshold.
        higher_is_worse: If True, values >= thresholds are worse
            (used for usage percentages). If False, the comparison is
            inverted.

    Returns:
        One of "healthy", "warning", "critical".
    """
    if higher_is_worse:
        if value >= critical:
            return "critical"
        if value >= warning:
            return "warning"
        return "healthy"
    else:
        if value <= critical:
            return "critical"
        if value <= warning:
            return "warning"
        return "healthy"


def worst_status(*statuses: str) -> str:
    """
    Return the worst (most severe) status out of the given list.

    Severity order: critical > warning > healthy > unknown.
    """
    severity = {"critical": 3, "warning": 2, "healthy": 1, "unknown": 0}
    if not statuses:
        return "unknown"
    return max(statuses, key=lambda s: severity.get(s, 0))
