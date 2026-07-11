"""
health_evaluator.py
====================
Orchestrates all individual check modules for a single server, handles
connection and per-check error isolation (a failure in one check must
not prevent the others from running), and produces one aggregated
result dictionary per server plus an overall health status.
"""

import time
from typing import Dict

from modules import cpu_check, disk_check, memory_check, mount_check, process_check, service_check, system_info
from modules.config_loader import ServerConfig
from modules.logger import get_logger
from modules.ssh_connector import SSHConnectionError, SSHConnector
from modules.utils import worst_status

logger = get_logger(__name__)


def evaluate_server(server: ServerConfig) -> Dict:
    """
    Run every health check against a single server and aggregate the
    results into one report-ready dictionary.

    Any exception raised while connecting produces a single 'critical'
    result for the whole server (SSH unreachable). Any exception raised
    by an individual check is caught, logged, and recorded as an
    'unknown' status for that check only, so the rest of the checks
    still run.

    Args:
        server: The ServerConfig describing how to connect.

    Returns:
        A dictionary describing the full health of the server, always
        containing at least: hostname, ip, ssh_reachable, status,
        error (if any), and check_duration_seconds.
    """
    start_time = time.monotonic()
    logger.info("Starting health check for %s (%s)", server.hostname, server.ip)

    base_result = {
        "hostname": server.hostname,
        "ip": server.ip,
        "ssh_reachable": False,
        "status": "critical",
        "error": None,
    }

    try:
        with SSHConnector(server) as conn:
            base_result["ssh_reachable"] = True

            info = _safe_check("system_info", lambda: system_info.get_system_info(conn))
            cpu = _safe_check("cpu", lambda: cpu_check.get_cpu_status(conn))
            memory = _safe_check("memory", lambda: memory_check.get_memory_status(conn))
            disk = _safe_check("disk", lambda: disk_check.get_disk_status(conn))
            mounts = _safe_check("mounts", lambda: mount_check.get_mount_status(conn, server))
            processes = _safe_check("processes", lambda: process_check.get_process_status(conn, server))
            services = _safe_check("services", lambda: service_check.get_service_status(conn, server))

            overall_status = worst_status(
                cpu.get("status", "unknown"),
                memory.get("status", "unknown"),
                disk.get("status", "unknown"),
                mounts.get("status", "unknown"),
                processes.get("status", "unknown"),
                services.get("status", "unknown"),
            )

            base_result.update({
                "status": overall_status,
                "system_info": info,
                "cpu": cpu,
                "memory": memory,
                "disk": disk,
                "mounts": mounts,
                "processes": processes,
                "services": services,
            })

    except SSHConnectionError as exc:
        base_result["error"] = str(exc)
        logger.error("Health check failed for %s: %s", server.hostname, exc)

    base_result["check_duration_seconds"] = round(time.monotonic() - start_time, 2)
    logger.info(
        "Completed health check for %s: status=%s duration=%.2fs",
        server.hostname, base_result["status"], base_result["check_duration_seconds"],
    )
    return base_result


def _safe_check(name: str, func) -> Dict:
    """
    Run a single check function, catching and logging any exception so
    that one failing check does not abort the others.

    Args:
        name: Human-readable name of the check (for logging).
        func: A zero-argument callable that performs the check.

    Returns:
        The check's result dict, or a minimal {'status': 'unknown',
        'error': ...} dict if it raised.
    """
    try:
        return func()
    except Exception as exc:  # noqa: BLE001 - intentionally broad to isolate failures
        logger.error("Check '%s' raised an unexpected error: %s", name, exc, exc_info=True)
        return {"status": "unknown", "error": str(exc)}
