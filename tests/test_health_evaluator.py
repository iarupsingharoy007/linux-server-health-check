"""
Unit tests for modules.health_evaluator.

Uses unittest.mock to simulate SSH connections and command output so
tests run without any real network access or Linux servers.
"""

import unittest
from unittest.mock import MagicMock, patch

from modules.config_loader import ServerConfig
from modules.health_evaluator import evaluate_server
from modules.ssh_connector import SSHConnectionError


def _make_server() -> ServerConfig:
    return ServerConfig(
        hostname="test-host",
        ip="127.0.0.1",
        username="tester",
        password="secret",
        expected_mounts=["/"],
        expected_processes=["nginx"],
        expected_services=["sshd"],
    )


class TestEvaluateServer(unittest.TestCase):
    @patch("modules.health_evaluator.SSHConnector")
    def test_unreachable_server_returns_critical(self, mock_connector_cls):
        mock_connector_cls.return_value.__enter__.side_effect = SSHConnectionError("no route to host")

        result = evaluate_server(_make_server())

        self.assertFalse(result["ssh_reachable"])
        self.assertEqual(result["status"], "critical")
        self.assertIn("no route to host", result["error"])

    @patch("modules.health_evaluator.system_info.get_system_info")
    @patch("modules.health_evaluator.service_check.get_service_status")
    @patch("modules.health_evaluator.process_check.get_process_status")
    @patch("modules.health_evaluator.mount_check.get_mount_status")
    @patch("modules.health_evaluator.disk_check.get_disk_status")
    @patch("modules.health_evaluator.memory_check.get_memory_status")
    @patch("modules.health_evaluator.cpu_check.get_cpu_status")
    @patch("modules.health_evaluator.SSHConnector")
    def test_healthy_server_aggregates_to_healthy(
        self, mock_connector_cls, mock_cpu, mock_mem, mock_disk,
        mock_mounts, mock_procs, mock_services, mock_sysinfo,
    ):
        mock_connector_cls.return_value.__enter__.return_value = MagicMock()

        mock_sysinfo.return_value = {"hostname": "test-host"}
        mock_cpu.return_value = {"status": "healthy"}
        mock_mem.return_value = {"status": "healthy"}
        mock_disk.return_value = {"status": "healthy", "filesystems": []}
        mock_mounts.return_value = {"status": "healthy", "missing": []}
        mock_procs.return_value = {"status": "healthy", "missing": []}
        mock_services.return_value = {"status": "healthy", "missing": []}

        result = evaluate_server(_make_server())

        self.assertTrue(result["ssh_reachable"])
        self.assertEqual(result["status"], "healthy")

    @patch("modules.health_evaluator.system_info.get_system_info")
    @patch("modules.health_evaluator.service_check.get_service_status")
    @patch("modules.health_evaluator.process_check.get_process_status")
    @patch("modules.health_evaluator.mount_check.get_mount_status")
    @patch("modules.health_evaluator.disk_check.get_disk_status")
    @patch("modules.health_evaluator.memory_check.get_memory_status")
    @patch("modules.health_evaluator.cpu_check.get_cpu_status")
    @patch("modules.health_evaluator.SSHConnector")
    def test_one_critical_check_makes_overall_critical(
        self, mock_connector_cls, mock_cpu, mock_mem, mock_disk,
        mock_mounts, mock_procs, mock_services, mock_sysinfo,
    ):
        mock_connector_cls.return_value.__enter__.return_value = MagicMock()

        mock_sysinfo.return_value = {"hostname": "test-host"}
        mock_cpu.return_value = {"status": "healthy"}
        mock_mem.return_value = {"status": "healthy"}
        mock_disk.return_value = {"status": "critical", "filesystems": []}
        mock_mounts.return_value = {"status": "healthy", "missing": []}
        mock_procs.return_value = {"status": "healthy", "missing": []}
        mock_services.return_value = {"status": "healthy", "missing": []}

        result = evaluate_server(_make_server())

        self.assertEqual(result["status"], "critical")

    @patch("modules.health_evaluator.system_info.get_system_info")
    @patch("modules.health_evaluator.service_check.get_service_status")
    @patch("modules.health_evaluator.process_check.get_process_status")
    @patch("modules.health_evaluator.mount_check.get_mount_status")
    @patch("modules.health_evaluator.disk_check.get_disk_status")
    @patch("modules.health_evaluator.memory_check.get_memory_status")
    @patch("modules.health_evaluator.cpu_check.get_cpu_status")
    @patch("modules.health_evaluator.SSHConnector")
    def test_check_exception_is_isolated(
        self, mock_connector_cls, mock_cpu, mock_mem, mock_disk,
        mock_mounts, mock_procs, mock_services, mock_sysinfo,
    ):
        """A single check raising an exception should not abort the others."""
        mock_connector_cls.return_value.__enter__.return_value = MagicMock()

        mock_sysinfo.return_value = {"hostname": "test-host"}
        mock_cpu.side_effect = RuntimeError("boom")
        mock_mem.return_value = {"status": "healthy"}
        mock_disk.return_value = {"status": "healthy", "filesystems": []}
        mock_mounts.return_value = {"status": "healthy", "missing": []}
        mock_procs.return_value = {"status": "healthy", "missing": []}
        mock_services.return_value = {"status": "healthy", "missing": []}

        result = evaluate_server(_make_server())

        self.assertEqual(result["cpu"]["status"], "unknown")
        self.assertEqual(result["memory"]["status"], "healthy")


if __name__ == "__main__":
    unittest.main()
