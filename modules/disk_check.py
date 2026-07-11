"""
disk_check.py
=============
Collects disk usage information for every mounted filesystem on a
remote server using `df -hP`, and classifies each filesystem's health
against configured thresholds.
"""

from typing import Dict, List

from config.settings import THRESHOLDS
from modules.logger import get_logger
from modules.ssh_connector import SSHConnector
from modules.utils import classify, parse_float, safe_run, worst_status

logger = get_logger(__name__)

# Pseudo/virtual filesystems that should be excluded from disk reporting.
_EXCLUDED_FS_TYPES = {"tmpfs", "devtmpfs", "overlay", "squashfs", "proc", "sysfs", "cgroup"}


def get_disk_status(conn: SSHConnector) -> Dict:
    """
    Determine disk usage for all real, mounted filesystems.

    Args:
        conn: An active SSHConnector.

    Returns:
        A dict with:
            - filesystems: list of per-filesystem dicts (filesystem,
              mount_point, size, used, available, use_percent, status)
            - status: worst status across all filesystems
    """
    df_output = safe_run(
        conn,
        "df -hP -x tmpfs -x devtmpfs -x overlay -x squashfs 2>/dev/null | tail -n +2",
        default="",
    )

    filesystems: List[Dict] = []
    for line in df_output.splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue

        filesystem, size, used, available, use_percent_raw, mount_point = (
            parts[0], parts[1], parts[2], parts[3], parts[4], " ".join(parts[5:])
        )

        use_percent = parse_float(use_percent_raw)
        fs_status = classify(
            use_percent, THRESHOLDS["disk"]["warning"], THRESHOLDS["disk"]["critical"]
        )

        filesystems.append({
            "filesystem": filesystem,
            "mount_point": mount_point,
            "size": size,
            "used": used,
            "available": available,
            "use_percent": use_percent,
            "status": fs_status,
        })

    overall = worst_status(*(fs["status"] for fs in filesystems)) if filesystems else "unknown"

    result = {
        "filesystems": filesystems,
        "status": overall,
    }
    logger.debug("Disk status for %s: %d filesystems, overall=%s",
                 conn.server.hostname, len(filesystems), overall)
    return result
