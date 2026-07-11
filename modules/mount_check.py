"""
mount_check.py
===============
Validates that a server's expected mount points (e.g. /, /home, /opt,
/app, /data) actually exist. Any missing mount is reported as a
critical finding, since it typically indicates a failed disk attach,
misconfiguration, or incomplete provisioning.
"""

from typing import Dict, List

from modules.config_loader import ServerConfig
from modules.logger import get_logger
from modules.ssh_connector import SSHConnector
from modules.utils import safe_run, worst_status

logger = get_logger(__name__)


def get_mount_status(conn: SSHConnector, server: ServerConfig) -> Dict:
    """
    Verify that each of the server's expected mount points is present.

    Args:
        conn: An active SSHConnector.
        server: The ServerConfig, which carries the list of expected
            mount points (falls back to the global default list).

    Returns:
        A dict with:
            - mounts: list of dicts (mount_point, present: bool, status)
            - missing: list of missing mount point paths
            - status: 'healthy' if all present, else 'critical'
    """
    mount_output = safe_run(conn, "mount | awk '{print $3}'", default="")
    active_mounts = set(mount_output.splitlines())

    expected = [m.strip() for m in server.expected_mounts if m.strip()]

    mounts: List[Dict] = []
    missing: List[str] = []

    for mount_point in expected:
        present = mount_point in active_mounts
        mounts.append({
            "mount_point": mount_point,
            "present": present,
            "status": "healthy" if present else "critical",
        })
        if not present:
            missing.append(mount_point)

    overall = worst_status(*(m["status"] for m in mounts)) if mounts else "healthy"

    result = {
        "mounts": mounts,
        "missing": missing,
        "status": overall,
    }
    logger.debug("Mount status for %s: missing=%s", conn.server.hostname, missing)
    return result
