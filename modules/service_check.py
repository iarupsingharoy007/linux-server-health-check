"""
service_check.py
==================
Checks the status of a configurable list of system services (e.g.
sshd, cron, nginx, docker, tomcat) using `systemctl`, falling back to
`service` on systems without systemd.
"""

from typing import Dict, List

from modules.config_loader import ServerConfig
from modules.logger import get_logger
from modules.ssh_connector import SSHConnector
from modules.utils import safe_run, worst_status

logger = get_logger(__name__)


def get_service_status(conn: SSHConnector, server: ServerConfig) -> Dict:
    """
    Check whether each expected service is active.

    Tries `systemctl is-active <service>` first; if systemctl is not
    available, falls back to `service <service> status`.

    Args:
        conn: An active SSHConnector.
        server: The ServerConfig, which carries the list of expected
            services (falls back to the global default list).

    Returns:
        A dict with:
            - services: list of dicts (name, active: bool, state, status)
            - missing: list of inactive/missing service names
            - status: 'healthy' if all active, else 'warning'
    """
    expected = [s.strip() for s in server.expected_services if s.strip()]

    # Detect systemd availability once per server.
    has_systemctl = safe_run(conn, "command -v systemctl", default="") != ""

    services: List[Dict] = []
    missing: List[str] = []

    for service_name in expected:
        if has_systemctl:
            state = safe_run(
                conn, f"systemctl is-active {service_name} 2>/dev/null", default="unknown"
            ).strip() or "unknown"
            active = state == "active"
        else:
            output = safe_run(conn, f"service {service_name} status 2>&1", default="")
            active = "running" in output.lower()
            state = "running" if active else "not running"

        services.append({
            "name": service_name,
            "active": active,
            "state": state,
            "status": "healthy" if active else "warning",
        })
        if not active:
            missing.append(service_name)

    overall = worst_status(*(s["status"] for s in services)) if services else "healthy"

    result = {
        "services": services,
        "missing": missing,
        "status": overall,
    }
    logger.debug("Service status for %s: missing=%s", conn.server.hostname, missing)
    return result
