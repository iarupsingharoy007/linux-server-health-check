"""Unit tests for modules.config_loader."""

import json
import os
import tempfile
import unittest

from modules.config_loader import ConfigError, load_servers


class TestLoadServers(unittest.TestCase):
    def _write_temp_json(self, data) -> str:
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(data, handle)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_load_valid_servers(self):
        path = self._write_temp_json({
            "servers": [
                {"hostname": "web01", "ip": "10.0.0.1", "username": "admin", "password": "secret"}
            ]
        })
        servers = load_servers(path)
        self.assertEqual(len(servers), 1)
        self.assertEqual(servers[0].hostname, "web01")
        self.assertEqual(servers[0].auth_method(), "password")

    def test_missing_file_raises(self):
        with self.assertRaises(ConfigError):
            load_servers("/nonexistent/path/servers.json")

    def test_invalid_json_raises(self):
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        handle.write("{not valid json")
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        with self.assertRaises(ConfigError):
            load_servers(handle.name)

    def test_missing_required_field_raises(self):
        path = self._write_temp_json({"servers": [{"hostname": "web01"}]})
        with self.assertRaises(ConfigError):
            load_servers(path)

    def test_missing_auth_method_raises(self):
        path = self._write_temp_json({
            "servers": [{"hostname": "web01", "ip": "10.0.0.1", "username": "admin"}]
        })
        with self.assertRaises(ConfigError):
            load_servers(path)

    def test_ssh_key_auth_method_detected(self):
        path = self._write_temp_json({
            "servers": [{
                "hostname": "web01", "ip": "10.0.0.1",
                "username": "admin", "ssh_key_path": "~/.ssh/id_rsa",
            }]
        })
        servers = load_servers(path)
        self.assertEqual(servers[0].auth_method(), "key")

    def test_empty_server_list_raises(self):
        path = self._write_temp_json({"servers": []})
        with self.assertRaises(ConfigError):
            load_servers(path)


if __name__ == "__main__":
    unittest.main()
