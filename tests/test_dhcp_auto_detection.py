"""Tests for DHCP auto-detection and SSH push functionality.

Validates:
- Debounce behaviour in _update_dhcp_auto_detection (3 consecutive readings)
- State persistence via _save_system_settings
- SSH push via _push_dhcp_config (mocked subprocess)
- Edge cases: SSH key missing, partial failure, timeout
"""

import asyncio
import importlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
        "SSH_KEY_PATH": str(tmp_path / "id_pihole_sentinel"),
        "PRIMARY_SSH_USER": "root",
        "PRIMARY_SSH_PORT": "22",
        "SECONDARY_SSH_USER": "root",
        "SECONDARY_SSH_PORT": "22",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    sys.modules.pop("dashboard.monitor", None)
    mod = importlib.import_module("dashboard.monitor")
    return mod


# ─────────────────────────────────────────────────────────────────────
# _update_dhcp_auto_detection — debounce
# ─────────────────────────────────────────────────────────────────────

class TestDhcpAutoDetection:
    """Test DHCP auto-detection debounce logic."""

    @pytest.mark.asyncio
    async def test_no_change_when_state_matches(self, monitor):
        """When observed state matches current, counter stays at 0."""
        monitor._dhcp_auto_detected = True
        monitor._dhcp_detect_counter = 0

        with patch.object(monitor, '_push_dhcp_config', new_callable=AsyncMock) as mock_push:
            await monitor._update_dhcp_auto_detection(True, False)

        assert monitor._dhcp_auto_detected is True
        assert monitor._dhcp_detect_counter == 0
        mock_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_counter_increments_on_different_state(self, monitor):
        """When observed state differs, counter increments but state doesn't change yet."""
        monitor._dhcp_auto_detected = True
        monitor._dhcp_detect_counter = 0

        with patch.object(monitor, '_push_dhcp_config', new_callable=AsyncMock):
            with patch.object(monitor, 'log_event', new_callable=AsyncMock):
                await monitor._update_dhcp_auto_detection(False, False)

        assert monitor._dhcp_auto_detected is True  # Not changed yet
        assert monitor._dhcp_detect_counter == 1

    @pytest.mark.asyncio
    async def test_no_change_below_threshold(self, monitor):
        """State doesn't change until threshold (3) is reached."""
        monitor._dhcp_auto_detected = True
        monitor._dhcp_detect_counter = 0

        with patch.object(monitor, '_push_dhcp_config', new_callable=AsyncMock) as mock_push:
            with patch.object(monitor, 'log_event', new_callable=AsyncMock):
                # 2 readings — below threshold
                await monitor._update_dhcp_auto_detection(False, False)
                await monitor._update_dhcp_auto_detection(False, False)

        assert monitor._dhcp_auto_detected is True
        assert monitor._dhcp_detect_counter == 2
        mock_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_state_changes_at_threshold(self, monitor):
        """State changes after 3 consecutive different readings."""
        monitor._dhcp_auto_detected = True
        monitor._dhcp_detect_counter = 0

        with patch.object(monitor, '_push_dhcp_config', new_callable=AsyncMock, return_value=True) as mock_push:
            with patch.object(monitor, 'log_event', new_callable=AsyncMock):
                with patch.object(monitor, '_save_system_settings'):
                    await monitor._update_dhcp_auto_detection(False, False)
                    await monitor._update_dhcp_auto_detection(False, False)
                    await monitor._update_dhcp_auto_detection(False, False)

        assert monitor._dhcp_auto_detected is False
        assert monitor._dhcp_detect_counter == 0
        mock_push.assert_called_once_with(False)

    @pytest.mark.asyncio
    async def test_counter_resets_when_state_matches_again(self, monitor):
        """If observed state flips back before threshold, counter resets."""
        monitor._dhcp_auto_detected = True
        monitor._dhcp_detect_counter = 0

        with patch.object(monitor, '_push_dhcp_config', new_callable=AsyncMock) as mock_push:
            with patch.object(monitor, 'log_event', new_callable=AsyncMock):
                await monitor._update_dhcp_auto_detection(False, False)  # counter=1
                await monitor._update_dhcp_auto_detection(False, False)  # counter=2
                await monitor._update_dhcp_auto_detection(True, False)   # matches → reset

        assert monitor._dhcp_auto_detected is True
        assert monitor._dhcp_detect_counter == 0
        mock_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_either_pihole_with_dhcp_means_active(self, monitor):
        """DHCP is 'in use' if either Pi-hole has it active."""
        monitor._dhcp_auto_detected = False
        monitor._dhcp_detect_counter = 0

        with patch.object(monitor, '_push_dhcp_config', new_callable=AsyncMock, return_value=True):
            with patch.object(monitor, 'log_event', new_callable=AsyncMock):
                with patch.object(monitor, '_save_system_settings'):
                    # Only secondary has DHCP — should still count as active
                    await monitor._update_dhcp_auto_detection(False, True)
                    await monitor._update_dhcp_auto_detection(False, True)
                    await monitor._update_dhcp_auto_detection(False, True)

        assert monitor._dhcp_auto_detected is True

    @pytest.mark.asyncio
    async def test_state_persisted_to_settings(self, monitor, tmp_path):
        """State change is persisted to notify_settings.json."""
        config_path = tmp_path / "notify_settings.json"
        monitor.CONFIG["notify_config_path"] = str(config_path)
        monitor._dhcp_auto_detected = True
        monitor._dhcp_detect_counter = 0

        with patch.object(monitor, '_push_dhcp_config', new_callable=AsyncMock, return_value=True):
            with patch.object(monitor, 'log_event', new_callable=AsyncMock):
                await monitor._update_dhcp_auto_detection(False, False)
                await monitor._update_dhcp_auto_detection(False, False)
                await monitor._update_dhcp_auto_detection(False, False)

        data = json.loads(config_path.read_text())
        assert data["system"]["dhcp_failover"] is False

    @pytest.mark.asyncio
    async def test_skip_when_both_none(self, monitor):
        """When both readings are None (API unreachable), detection is skipped."""
        monitor._dhcp_auto_detected = True
        monitor._dhcp_detect_counter = 0

        with patch.object(monitor, '_push_dhcp_config', new_callable=AsyncMock) as mock_push:
            # 10 polls with None — should never change state
            for _ in range(10):
                await monitor._update_dhcp_auto_detection(None, None)

        assert monitor._dhcp_auto_detected is True
        assert monitor._dhcp_detect_counter == 0
        mock_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_when_one_none_one_true(self, monitor):
        """When one reading is None, detection is skipped even if other is True."""
        monitor._dhcp_auto_detected = False
        monitor._dhcp_detect_counter = 0

        with patch.object(monitor, '_push_dhcp_config', new_callable=AsyncMock) as mock_push:
            for _ in range(5):
                await monitor._update_dhcp_auto_detection(None, True)

        assert monitor._dhcp_auto_detected is False
        assert monitor._dhcp_detect_counter == 0
        mock_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_when_one_none_one_false(self, monitor):
        """When one reading is None, detection is skipped even if other is False."""
        monitor._dhcp_auto_detected = True
        monitor._dhcp_detect_counter = 0

        with patch.object(monitor, '_push_dhcp_config', new_callable=AsyncMock) as mock_push:
            for _ in range(5):
                await monitor._update_dhcp_auto_detection(True, None)

        assert monitor._dhcp_auto_detected is True
        assert monitor._dhcp_detect_counter == 0
        mock_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_counter_frozen_during_unknown(self, monitor):
        """Debounce counter doesn't advance during None readings."""
        monitor._dhcp_auto_detected = True
        monitor._dhcp_detect_counter = 0

        with patch.object(monitor, '_push_dhcp_config', new_callable=AsyncMock) as mock_push:
            with patch.object(monitor, 'log_event', new_callable=AsyncMock):
                # 2 real different readings → counter=2
                await monitor._update_dhcp_auto_detection(False, False)
                await monitor._update_dhcp_auto_detection(False, False)
                assert monitor._dhcp_detect_counter == 2

                # API goes down — None readings shouldn't advance counter
                await monitor._update_dhcp_auto_detection(None, None)
                await monitor._update_dhcp_auto_detection(None, False)
                assert monitor._dhcp_detect_counter == 2  # frozen

                # API comes back with same different reading → threshold reached
                with patch.object(monitor, '_save_system_settings'):
                    await monitor._update_dhcp_auto_detection(False, False)

        assert monitor._dhcp_auto_detected is False
        assert monitor._dhcp_detect_counter == 0
        mock_push.assert_called_once_with(False)


# ─────────────────────────────────────────────────────────────────────
# _push_dhcp_config — SSH push
# ─────────────────────────────────────────────────────────────────────

class TestPushDhcpConfig:
    """Test SSH push of DHCP config to Pi-holes."""

    @pytest.mark.asyncio
    async def test_returns_false_when_no_ssh_key(self, monitor):
        """When SSH key doesn't exist, returns False without attempting SSH."""
        with patch.object(monitor, '_ssh_key_available', return_value=False):
            result = await monitor._push_dhcp_config(True)
        assert result is False

    @pytest.mark.asyncio
    async def test_push_success_both_nodes(self, monitor, tmp_path):
        """Successful push to both nodes returns True."""
        # Create fake SSH key so _ssh_key_available returns True
        ssh_key = tmp_path / "id_pihole_sentinel"
        ssh_key.write_text("fake-key")
        monitor.CONFIG["ssh"]["key_path"] = str(ssh_key)

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
            result = await monitor._push_dhcp_config(True)

        assert result is True

    @pytest.mark.asyncio
    async def test_push_failure_both_nodes(self, monitor, tmp_path):
        """Failed push to both nodes returns False."""
        ssh_key = tmp_path / "id_pihole_sentinel"
        ssh_key.write_text("fake-key")
        monitor.CONFIG["ssh"]["key_path"] = str(ssh_key)

        mock_proc = AsyncMock()
        mock_proc.returncode = 255
        mock_proc.communicate = AsyncMock(return_value=(b"", b"Connection refused"))

        with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
            result = await monitor._push_dhcp_config(False)

        assert result is False

    @pytest.mark.asyncio
    async def test_push_timeout_returns_false(self, monitor, tmp_path):
        """SSH timeout returns False."""
        ssh_key = tmp_path / "id_pihole_sentinel"
        ssh_key.write_text("fake-key")
        monitor.CONFIG["ssh"]["key_path"] = str(ssh_key)

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
                result = await monitor._push_dhcp_config(True)

        assert result is False

    @pytest.mark.asyncio
    async def test_push_uses_correct_sed_command(self, monitor, tmp_path):
        """Push constructs correct sed command for DHCP_ENABLED."""
        ssh_key = tmp_path / "id_pihole_sentinel"
        ssh_key.write_text("fake-key")
        monitor.CONFIG["ssh"]["key_path"] = str(ssh_key)

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        calls = []

        async def capture_exec(*args, **kwargs):
            calls.append(args)
            return mock_proc

        with patch('asyncio.create_subprocess_exec', side_effect=capture_exec):
            await monitor._push_dhcp_config(False)

        # Both calls should contain the sed command with DHCP_ENABLED=false
        assert len(calls) == 2
        for call_args in calls:
            # The sed command is the last positional arg
            sed_cmd = call_args[-1]
            assert "DHCP_ENABLED=false" in sed_cmd


# ─────────────────────────────────────────────────────────────────────
# _ssh_key_available
# ─────────────────────────────────────────────────────────────────────

class TestSshKeyAvailable:
    """Test SSH key availability check."""

    def test_returns_true_when_key_exists(self, monitor, tmp_path):
        """Returns True when SSH key file exists."""
        key_path = tmp_path / "id_pihole_sentinel"
        key_path.write_text("fake-key")
        monitor.CONFIG["ssh"]["key_path"] = str(key_path)

        assert monitor._ssh_key_available() is True

    def test_returns_false_when_key_missing(self, monitor, tmp_path):
        """Returns False when SSH key file doesn't exist."""
        monitor.CONFIG["ssh"]["key_path"] = str(tmp_path / "nonexistent")

        assert monitor._ssh_key_available() is False
