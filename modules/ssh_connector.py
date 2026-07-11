"""
ssh_connector.py
================
Handles SSH connectivity and remote command execution using Paramiko.

This module is intentionally the only place in the codebase that touches
Paramiko directly, so authentication logic, timeouts, and retries are
handled consistently for every check module.
"""

import socket
import time
from typing import Optional, Tuple

import paramiko

from config import settings
from modules.config_loader import ServerConfig
from modules.logger import get_logger

logger = get_logger(__name__)


class SSHConnectionError(Exception):
    """Raised when an SSH connection cannot be established after retries."""


class CommandExecutionError(Exception):
    """Raised when a remote command fails or times out."""


class SSHConnector:
    """
    Manages a single SSH connection to a remote Linux server and provides
    a simple, safe interface for running commands with timeouts.

    Usage:
        with SSHConnector(server_config) as conn:
            output = conn.run("uptime")
    """

    def __init__(self, server: ServerConfig):
        self.server = server
        self._client: Optional[paramiko.SSHClient] = None

    def __enter__(self) -> "SSHConnector":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def connect(self) -> None:
        """
        Establish the SSH connection, retrying on transient failures
        according to ``settings.MAX_RETRIES``.

        Raises:
            SSHConnectionError: If the connection cannot be established.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, settings.MAX_RETRIES + 2):
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                connect_kwargs = dict(
                    hostname=self.server.ip,
                    port=self.server.port,
                    username=self.server.username,
                    timeout=settings.SSH_CONNECT_TIMEOUT,
                    banner_timeout=settings.SSH_CONNECT_TIMEOUT,
                    auth_timeout=settings.SSH_CONNECT_TIMEOUT,
                )
                if self.server.ssh_key_path:
                    connect_kwargs["key_filename"] = self.server.ssh_key_path
                else:
                    connect_kwargs["password"] = self.server.password

                client.connect(**connect_kwargs)
                self._client = client
                logger.info(
                    "Connected to %s (%s) on attempt %d",
                    self.server.hostname, self.server.ip, attempt,
                )
                return
            except paramiko.AuthenticationException as exc:
                last_error = exc
                logger.error(
                    "Authentication failed for %s (%s): %s",
                    self.server.hostname, self.server.ip, exc,
                )
                break  # No point retrying bad credentials
            except (paramiko.SSHException, socket.timeout, socket.error, OSError) as exc:
                last_error = exc
                logger.warning(
                    "Connection attempt %d/%d to %s (%s) failed: %s",
                    attempt, settings.MAX_RETRIES + 1,
                    self.server.hostname, self.server.ip, exc,
                )
                if attempt <= settings.MAX_RETRIES:
                    time.sleep(settings.RETRY_DELAY_SECONDS)

        raise SSHConnectionError(
            f"Could not connect to {self.server.hostname} ({self.server.ip}): {last_error}"
        )

    def run(self, command: str, timeout: Optional[int] = None) -> Tuple[str, str, int]:
        """
        Execute a command on the remote server.

        Args:
            command: The shell command to execute.
            timeout: Optional override for the command timeout in seconds.

        Returns:
            A tuple of (stdout, stderr, exit_status).

        Raises:
            CommandExecutionError: If the command cannot be executed
                (e.g. connection dropped) or times out.
        """
        if self._client is None:
            raise CommandExecutionError("Not connected. Call connect() first.")

        cmd_timeout = timeout or settings.SSH_COMMAND_TIMEOUT
        try:
            stdin, stdout, stderr = self._client.exec_command(command, timeout=cmd_timeout)
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode("utf-8", errors="replace").strip()
            err = stderr.read().decode("utf-8", errors="replace").strip()

            if exit_status != 0:
                logger.warning(
                    "Command '%s' on %s exited with status %d: %s",
                    command, self.server.hostname, exit_status, err,
                )
            return out, err, exit_status
        except socket.timeout as exc:
            logger.error(
                "Command '%s' on %s timed out after %ds",
                command, self.server.hostname, cmd_timeout,
            )
            raise CommandExecutionError(
                f"Command timed out on {self.server.hostname}: {command}"
            ) from exc
        except paramiko.SSHException as exc:
            logger.error("Command '%s' on %s failed: %s", command, self.server.hostname, exc)
            raise CommandExecutionError(
                f"Command failed on {self.server.hostname}: {command} ({exc})"
            ) from exc

    def close(self) -> None:
        """Close the SSH connection if open."""
        if self._client is not None:
            self._client.close()
            self._client = None
            logger.debug("Closed SSH connection to %s", self.server.hostname)
