"""
cpu_check.py
============
Collects CPU usage and load average from a remote server and classifies
the result against the configured thresholds.
"""

from typing import Dict

from config.settings import THRESHOLDS
from modules.logger import get_logger
from modules.ssh_connector import SSHConnector
from modules.utils import classify, parse_float, safe_run

logger = get_logger(__name__)


def get_cpu_status(conn: SSHConnector) -> Dict:
    """
    Determine CPU usage percentage and load average, and classify health.

    Uses `top` in batch mode (portable across most distros) to compute
    instantaneous CPU usage, and `/proc/loadavg` for load averages.

    Args:
        conn: An active SSHConnector.

    Returns:
        A dict with keys: usage_percent, load_1, load_5, load_15,
        core_count, load_ratio, status.
    """
    # CPU usage via top: sum of user+system, or 100 - idle.
    top_output = safe_run(
        conn,
        "top -bn1 | grep -i '%Cpu' | awk '{print $8}'",
        default="",
    )
    idle_percent = parse_float(top_output, default=None) if top_output else None

    if idle_percent is None:
        # Fallback: mpstat, or vmstat-based estimate
        vmstat_output = safe_run(conn, "vmstat 1 2 | tail -1 | awk '{print $15}'", default="")
        idle_percent = parse_float(vmstat_output, default=100.0)

    usage_percent = round(max(0.0, 100.0 - idle_percent), 2)

    core_count_raw = safe_run(conn, "nproc", default="1")
    core_count = int(parse_float(core_count_raw, default=1.0)) or 1

    loadavg_raw = safe_run(conn, "cat /proc/loadavg", default="0 0 0")
    parts = loadavg_raw.split()
    load_1 = parse_float(parts[0]) if len(parts) > 0 else 0.0
    load_5 = parse_float(parts[1]) if len(parts) > 1 else 0.0
    load_15 = parse_float(parts[2]) if len(parts) > 2 else 0.0

    load_ratio = round(load_1 / core_count, 2) if core_count else 0.0

    cpu_status = classify(
        usage_percent, THRESHOLDS["cpu"]["warning"], THRESHOLDS["cpu"]["critical"]
    )
    load_status = classify(
        load_ratio, THRESHOLDS["load_average"]["warning"], THRESHOLDS["load_average"]["critical"]
    )

    from modules.utils import worst_status
    overall = worst_status(cpu_status, load_status)

    result = {
        "usage_percent": usage_percent,
        "load_1": load_1,
        "load_5": load_5,
        "load_15": load_15,
        "core_count": core_count,
        "load_ratio": load_ratio,
        "status": overall,
    }
    logger.debug("CPU status for %s: %s", conn.server.hostname, result)
    return result
