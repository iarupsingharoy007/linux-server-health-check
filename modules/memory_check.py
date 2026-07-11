"""
memory_check.py
================
Collects memory and swap usage from a remote server using `free -m`,
and classifies the results against configured thresholds.
"""

from typing import Dict

from config.settings import THRESHOLDS
from modules.logger import get_logger
from modules.ssh_connector import SSHConnector
from modules.utils import classify, parse_float, safe_run, worst_status

logger = get_logger(__name__)


def get_memory_status(conn: SSHConnector) -> Dict:
    """
    Determine memory and swap usage and classify health.

    Args:
        conn: An active SSHConnector.

    Returns:
        A dict with memory and swap totals/used/free (MB) and percentages,
        plus a combined status.
    """
    free_output = safe_run(conn, "free -m | grep -i mem", default="")
    mem_parts = free_output.split()

    mem_total = parse_float(mem_parts[1]) if len(mem_parts) > 1 else 0.0
    mem_used = parse_float(mem_parts[2]) if len(mem_parts) > 2 else 0.0
    mem_free = parse_float(mem_parts[3]) if len(mem_parts) > 3 else 0.0
    mem_available = parse_float(mem_parts[6]) if len(mem_parts) > 6 else mem_free

    mem_percent = round((mem_used / mem_total) * 100, 2) if mem_total else 0.0

    swap_output = safe_run(conn, "free -m | grep -i swap", default="")
    swap_parts = swap_output.split()

    swap_total = parse_float(swap_parts[1]) if len(swap_parts) > 1 else 0.0
    swap_used = parse_float(swap_parts[2]) if len(swap_parts) > 2 else 0.0
    swap_free = parse_float(swap_parts[3]) if len(swap_parts) > 3 else 0.0

    swap_percent = round((swap_used / swap_total) * 100, 2) if swap_total else 0.0

    mem_status = classify(
        mem_percent, THRESHOLDS["memory"]["warning"], THRESHOLDS["memory"]["critical"]
    )
    swap_status = classify(
        swap_percent, THRESHOLDS["swap"]["warning"], THRESHOLDS["swap"]["critical"]
    ) if swap_total > 0 else "healthy"

    overall = worst_status(mem_status, swap_status)

    result = {
        "mem_total_mb": mem_total,
        "mem_used_mb": mem_used,
        "mem_free_mb": mem_free,
        "mem_available_mb": mem_available,
        "mem_percent": mem_percent,
        "swap_total_mb": swap_total,
        "swap_used_mb": swap_used,
        "swap_free_mb": swap_free,
        "swap_percent": swap_percent,
        "status": overall,
    }
    logger.debug("Memory status for %s: %s", conn.server.hostname, result)
    return result
