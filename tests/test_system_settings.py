"""Tests for system settings API and DHCP failover toggle."""

import importlib
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def monitor(monkeypatch, tmp_path):
    """Import dashboard.monitor with test environment variables."""
    env = {
        "PRIMARY_IP": "10.10.100.10",
        "PRIMARY_PASSWORD": "test_password",
        "SECONDARY_IP": "10.10.100.20",
        "SECONDARY_PASSWORD": "test_password",
        "VIP_ADDRESS": "10.10.100.2",
        "CHECK_INTERVAL": "10",
        "DB_PATH": str(tmp_path / "monitor.db"),
        "API_KEY": "test_api_key",
        "NOTIFY_CONFIG_PATH": str(tmp_path / "notify_settings.json"),
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    sys.modules.pop("dashboard.monitor", None)
    mod = importlib.import_module("dashboard.monitor")
    return mod


# ─────────────────────────────────────────────────────────────────────
# _load_system_settings
# ─────────────────────────────────────────────────────────────────────

class TestLoadSystemSettings:
    """Test system settings loading from JSON config."""

    def test_default_when_file_missing(self, monitor):
        """When config file doesn't exist, default to dhcp_failover=True."""
        result = monitor._load_system_settings()
        assert result["dhcp_failover"] is True

    def test_default_when_system_key_missing(self, monitor, tmp_path):
        """When JSON exists but has no 'system' key, default to True."""
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text(json.dumps({"telegram": {"enabled": False}}))
        monitor.CONFIG["notify_config_path"] = str(config_path)

        result = monitor._load_system_settings()
        assert result["dhcp_failover"] is True

    def test_reads_dhcp_failover_false(self, monitor, tmp_path):
        """When system.dhcp_failover is false, return False."""
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text(json.dumps({
            "system": {"dhcp_failover": False}
        }))
        monitor.CONFIG["notify_config_path"] = str(config_path)

        result = monitor._load_system_settings()
        assert result["dhcp_failover"] is False

    def test_reads_dhcp_failover_true(self, monitor, tmp_path):
        """When system.dhcp_failover is true, return True."""
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text(json.dumps({
            "system": {"dhcp_failover": True}
        }))
        monitor.CONFIG["notify_config_path"] = str(config_path)

        result = monitor._load_system_settings()
        assert result["dhcp_failover"] is True

    def test_corrupted_json_returns_defaults(self, monitor, tmp_path):
        """When config file has invalid JSON, return defaults."""
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text("this is not json{{{")
        monitor.CONFIG["notify_config_path"] = str(config_path)

        result = monitor._load_system_settings()
        assert result["dhcp_failover"] is True


# ─────────────────────────────────────────────────────────────────────
# _save_system_settings
# ─────────────────────────────────────────────────────────────────────

class TestSaveSystemSettings:
    """Test system settings persistence."""

    def test_creates_new_file(self, monitor, tmp_path):
        """Save creates config file when none exists."""
        config_path = tmp_path / "subdir" / "notify_settings.json"
        monitor.CONFIG["notify_config_path"] = str(config_path)

        monitor._save_system_settings({"dhcp_failover": False})

        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert data["system"]["dhcp_failover"] is False

    def test_preserves_existing_settings(self, monitor, tmp_path):
        """Save preserves existing notification settings."""
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text(json.dumps({
            "telegram": {"enabled": True, "bot_token": "secret123"},
            "events": {"failover": True}
        }))
        monitor.CONFIG["notify_config_path"] = str(config_path)

        monitor._save_system_settings({"dhcp_failover": False})

        data = json.loads(config_path.read_text())
        assert data["system"]["dhcp_failover"] is False
        assert data["telegram"]["bot_token"] == "secret123"
        assert data["events"]["failover"] is True

    def test_file_permissions(self, monitor, tmp_path):
        """Saved config file has restricted permissions (0o600)."""
        config_path = tmp_path / "notify_settings.json"
        monitor.CONFIG["notify_config_path"] = str(config_path)

        monitor._save_system_settings({"dhcp_failover": True})

        perms = oct(os.stat(config_path).st_mode & 0o777)
        assert perms == "0o600"


# ─────────────────────────────────────────────────────────────────────
# Backward compatibility
# ─────────────────────────────────────────────────────────────────────

class TestBackwardCompatibility:
    """Existing installations without system settings should work unchanged."""

    def test_existing_config_without_system_key(self, monitor, tmp_path):
        """Old configs without 'system' key default to dhcp_failover=True."""
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text(json.dumps({
            "telegram": {"enabled": False},
            "events": {"failover": True, "recovery": True}
        }))
        monitor.CONFIG["notify_config_path"] = str(config_path)

        result = monitor._load_system_settings()
        assert result["dhcp_failover"] is True

    def test_cached_settings_available(self, monitor):
        """Module-level _system_settings cache is populated."""
        assert hasattr(monitor, '_system_settings')
        assert "dhcp_failover" in monitor._system_settings

    def test_default_is_enabled(self, monitor):
        """Default system settings have DHCP failover enabled."""
        # Fresh import with no config file → should default to True
        assert monitor._system_settings.get("dhcp_failover", True) is True
