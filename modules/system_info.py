"""
system_info.py
===============
Collects basic system identity information from a remote server:
hostname, IP, OS version, kernel version, uptime, and current
date/time.
"""

from typing import Dict

from modules.logger import get_logger
from modules.ssh_connector import SSHConnector
from modules.utils import safe_run

logger = get_logger(__name__)


def get_system_info(conn: SSHConnector) -> Dict[str, str]:
    """
    Gather identity/system information from the remote server.

    Args:
        conn: An active SSHConnector.

    Returns:
        A dictionary with keys: hostname, ip, os_version, kernel_version,
        uptime, current_datetime.
    """
    hostname = safe_run(conn, "hostname", default="unknown")

    ip_output = safe_run(conn, "hostname -I", default="")
    ip_address = ip_output.split()[0] if ip_output else conn.server.ip

    os_version = safe_run(
        conn,
        "cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'",
        default="Unknown OS",
    )

    kernel_version = safe_run(conn, "uname -r", default="unknown")

    uptime_raw = safe_run(conn, "uptime -p", default="")
    if not uptime_raw:
        uptime_raw = safe_run(conn, "uptime", default="unknown")

    current_datetime = safe_run(conn, "date '+%Y-%m-%d %H:%M:%S %Z'", default="unknown")

    info = {
        "hostname": hostname or "unknown",
        "ip": ip_address or conn.server.ip,
        "os_version": os_version or "Unknown OS",
        "kernel_version": kernel_version or "unknown",
        "uptime": uptime_raw or "unknown",
        "current_datetime": current_datetime or "unknown",
    }

    logger.debug("System info for %s: %s", conn.server.hostname, info)
    return info
