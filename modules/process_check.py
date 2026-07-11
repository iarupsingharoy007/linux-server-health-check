"""
process_check.py
=================
Verifies whether a configurable list of required processes (e.g. java,
python, nginx, tomcat, mysqld) are currently running on the remote
server.
"""

from typing import Dict, List

from modules.config_loader import ServerConfig
from modules.logger import get_logger
from modules.ssh_connector import SSHConnector
from modules.utils import safe_run, worst_status

logger = get_logger(__name__)


def get_process_status(conn: SSHConnector, server: ServerConfig) -> Dict:
    """
    Check whether each expected process is running using `pgrep`.

    Args:
        conn: An active SSHConnector.
        server: The ServerConfig, which carries the list of expected
            processes (falls back to the global default list).

    Returns:
        A dict with:
            - processes: list of dicts (name, running: bool, pid_count, status)
            - missing: list of process names not found
            - status: 'healthy' if all running, else 'warning'
    """
    expected = [p.strip() for p in server.expected_processes if p.strip()]

    processes: List[Dict] = []
    missing: List[str] = []

    for process_name in expected:
        output = safe_run(conn, f"pgrep -c -f {process_name}", default="0")
        try:
            pid_count = int(output.strip().splitlines()[0]) if output.strip() else 0
        except (ValueError, IndexError):
            pid_count = 0

        running = pid_count > 0
        processes.append({
            "name": process_name,
            "running": running,
            "pid_count": pid_count,
            "status": "healthy" if running else "warning",
        })
        if not running:
            missing.append(process_name)

    overall = worst_status(*(p["status"] for p in processes)) if processes else "healthy"

    result = {
        "processes": processes,
        "missing": missing,
        "status": overall,
    }
    logger.debug("Process status for %s: missing=%s", conn.server.hostname, missing)
    return result
