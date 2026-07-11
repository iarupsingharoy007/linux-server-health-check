"""
config_loader.py
=================
Loads and validates the ``servers.json`` inventory file that describes
which Linux servers the tool should connect to and how.

Keeping this in its own module means the rest of the application never
touches raw JSON or the filesystem directly.
"""

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional

from config import settings
from modules.logger import get_logger

logger = get_logger(__name__)


class ConfigError(Exception):
    """Raised when servers.json is missing, malformed, or invalid."""


@dataclass
class ServerConfig:
    """Typed representation of a single server entry from servers.json."""

    hostname: str
    ip: str
    username: str
    password: Optional[str] = None
    ssh_key_path: Optional[str] = None
    port: int = settings.SSH_PORT_DEFAULT
    expected_mounts: List[str] = field(default_factory=lambda: settings.EXPECTED_MOUNTS)
    expected_processes: List[str] = field(default_factory=lambda: settings.EXPECTED_PROCESSES)
    expected_services: List[str] = field(default_factory=lambda: settings.EXPECTED_SERVICES)

    def auth_method(self) -> str:
        """Return 'key' or 'password' depending on what was configured."""
        return "key" if self.ssh_key_path else "password"


def load_servers(path: Optional[str] = None) -> List[ServerConfig]:
    """
    Load and validate the server inventory file.

    Args:
        path: Optional override path to the JSON file. Defaults to
            ``settings.SERVERS_FILE``.

    Returns:
        A list of validated ``ServerConfig`` objects.

    Raises:
        ConfigError: If the file is missing, unreadable, malformed, or
            contains an entry missing required fields.
    """
    file_path = path or settings.SERVERS_FILE

    if not os.path.isfile(file_path):
        raise ConfigError(f"Server inventory file not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            raw_data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {file_path}: {exc}") from exc

    servers_raw = raw_data.get("servers", raw_data if isinstance(raw_data, list) else [])
    if not servers_raw:
        raise ConfigError(f"No servers defined in {file_path}")

    servers: List[ServerConfig] = []
    for index, entry in enumerate(servers_raw):
        try:
            servers.append(_build_server_config(entry))
        except KeyError as exc:
            raise ConfigError(
                f"Server entry #{index + 1} in {file_path} is missing required field {exc}"
            ) from exc

    logger.info("Loaded %d server(s) from %s", len(servers), file_path)
    return servers


def _build_server_config(entry: dict) -> ServerConfig:
    """Build a ServerConfig from a raw dict, applying defaults from settings."""
    required = ["hostname", "ip", "username"]
    for field_name in required:
        if field_name not in entry:
            raise KeyError(field_name)

    if "password" not in entry and "ssh_key_path" not in entry:
        raise ConfigError(
            f"Server '{entry.get('hostname')}' must define either "
            f"'password' or 'ssh_key_path'"
        )

    return ServerConfig(
        hostname=entry["hostname"],
        ip=entry["ip"],
        username=entry["username"],
        password=entry.get("password"),
        ssh_key_path=entry.get("ssh_key_path"),
        port=int(entry.get("port", settings.SSH_PORT_DEFAULT)),
        expected_mounts=entry.get("expected_mounts", settings.EXPECTED_MOUNTS),
        expected_processes=entry.get("expected_processes", settings.EXPECTED_PROCESSES),
        expected_services=entry.get("expected_services", settings.EXPECTED_SERVICES),
    )
