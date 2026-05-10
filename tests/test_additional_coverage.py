"""
Tests for additional monitor.py functions.

Covers: mask_sensitive_data, merge_settings, check_and_send_reminders,
get_snooze_status, set_snooze, cancel_snooze, and check_who_has_vip.
"""

import asyncio
import importlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Fixtures
# ============================================================================

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
    return importlib.import_module("dashboard.monitor")


# ============================================================================
# mask_sensitive_data tests
# ============================================================================

class TestMaskSensitiveData:
    """Tests for the credential masking helper."""

    def test_masks_telegram_bot_token(self, monitor):
        settings = {"telegram": {"bot_token": "1234567890:ABCDEFGHIJ"}}
        masked = monitor.mask_sensitive_data(settings)
        token = masked["telegram"]["bot_token"]
        assert token.startswith("••••")
        assert "GHIJ" in token  # last 4 chars preserved

    def test_masks_telegram_chat_id(self, monitor):
        settings = {"telegram": {"chat_id": "-1001234567890"}}
        masked = monitor.mask_sensitive_data(settings)
        chat_id = masked["telegram"]["chat_id"]
        assert chat_id.startswith("••••")

    def test_masks_discord_webhook_url(self, monitor):
        settings = {"discord": {"webhook_url": "https://discord.com/api/webhooks/1234/token"}}
        masked = monitor.mask_sensitive_data(settings)
        url = masked["discord"]["webhook_url"]
        assert url.startswith("••••")

    def test_masks_pushover_keys(self, monitor):
        settings = {
            "pushover": {
                "user_key": "uXXXXXXXXXXXXXXXXXXXX",
                "app_token": "aXXXXXXXXXXXXXXXXXXXX",
            }
        }
        masked = monitor.mask_sensitive_data(settings)
        assert masked["pushover"]["user_key"].startswith("••••")
        assert masked["pushover"]["app_token"].startswith("••••")

    def test_masks_webhook_url(self, monitor):
        settings = {"webhook": {"url": "https://example.com/hooks/secret123456789"}}
        masked = monitor.mask_sensitive_data(settings)
        assert masked["webhook"]["url"].startswith("••••")

    def test_empty_fields_not_masked(self, monitor):
        settings = {"telegram": {"bot_token": "", "chat_id": ""}}
        masked = monitor.mask_sensitive_data(settings)
        # Empty string → nothing to mask
        assert masked["telegram"]["bot_token"] == ""
        assert masked["telegram"]["chat_id"] == ""

    def test_does_not_modify_original(self, monitor):
        """mask_sensitive_data returns a deep copy; original is unchanged."""
        settings = {"telegram": {"bot_token": "secret-token"}}
        monitor.mask_sensitive_data(settings)
        assert settings["telegram"]["bot_token"] == "secret-token"

    def test_ntfy_topic_not_masked(self, monitor):
        """Ntfy topic and server are not sensitive and should pass through unchanged."""
        settings = {"ntfy": {"topic": "pihole-alerts", "server": "https://ntfy.sh"}}
        masked = monitor.mask_sensitive_data(settings)
        assert masked["ntfy"]["topic"] == "pihole-alerts"
        assert masked["ntfy"]["server"] == "https://ntfy.sh"


# ============================================================================
# merge_settings tests
# ============================================================================

class TestMergeSettings:
    """Tests for the settings merge helper."""

    def test_new_keys_are_added(self, monitor):
        existing = {"telegram": {"enabled": True}}
        new = {"discord": {"enabled": False}}
        merged = monitor.merge_settings(existing, new)
        assert merged["telegram"]["enabled"] is True
        assert merged["discord"]["enabled"] is False

    def test_none_value_preserves_existing(self, monitor):
        """None in new settings means keep existing value."""
        existing = {"telegram": {"bot_token": "secret"}}
        new = {"telegram": {"bot_token": None}}
        merged = monitor.merge_settings(existing, new)
        assert merged["telegram"]["bot_token"] == "secret"

    def test_new_value_overwrites_existing(self, monitor):
        existing = {"telegram": {"enabled": False}}
        new = {"telegram": {"enabled": True}}
        merged = monitor.merge_settings(existing, new)
        assert merged["telegram"]["enabled"] is True

    def test_masked_value_preserves_existing(self, monitor):
        """Masked values (starting with ••••) are rejected; existing is kept."""
        existing = {"telegram": {"bot_token": "original-secret"}}
        new = {"telegram": {"bot_token": "••••cret"}}  # looks masked
        merged = monitor.merge_settings(existing, new)
        assert merged["telegram"]["bot_token"] == "original-secret"

    def test_masked_value_empty_when_no_existing(self, monitor):
        """Masked values with no existing fallback become empty string."""
        existing = {}
        new = {"telegram": {"bot_token": "••••token"}}
        merged = monitor.merge_settings(existing, new)
        assert merged["telegram"]["bot_token"] == ""

    def test_existing_unchanged_keys_preserved(self, monitor):
        """Keys present in existing but absent from new are preserved."""
        existing = {"telegram": {"enabled": True, "bot_token": "secret", "chat_id": "123"}}
        new = {"telegram": {"enabled": False}}
        merged = monitor.merge_settings(existing, new)
        assert merged["telegram"]["bot_token"] == "secret"
        assert merged["telegram"]["chat_id"] == "123"


# ============================================================================
# check_and_send_reminders tests
# ============================================================================

class TestCheckAndSendReminders:
    """Tests for the reminder notification scheduler."""

    @pytest.mark.asyncio
    async def test_no_config_file_returns_silently(self, monitor, tmp_path):
        """When config file is missing, function returns without error."""
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "missing.json")
        await monitor.check_and_send_reminders()

    @pytest.mark.asyncio
    async def test_repeat_disabled_skips_reminders(self, monitor, tmp_path):
        """When repeat.enabled is False, no notifications are sent."""
        config = {
            "repeat": {"enabled": False, "interval": 30},
            "events": {"failover": True},
        }
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text(json.dumps(config))
        monitor.CONFIG["notify_config_path"] = str(config_path)

        with patch.object(monitor, "send_notification", new=AsyncMock()) as mock_notify:
            await monitor.check_and_send_reminders()

        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_interval_zero_skips_reminders(self, monitor, tmp_path):
        """When repeat.interval is 0, no notifications are sent."""
        config = {"repeat": {"enabled": True, "interval": 0}}
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text(json.dumps(config))
        monitor.CONFIG["notify_config_path"] = str(config_path)

        with patch.object(monitor, "send_notification", new=AsyncMock()) as mock_notify:
            await monitor.check_and_send_reminders()

        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_reminder_when_due(self, monitor, tmp_path):
        """Sends reminder notification when interval has elapsed and issue is active."""
        config = {"repeat": {"enabled": True, "interval": 30}}
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text(json.dumps(config))
        monitor.CONFIG["notify_config_path"] = str(config_path)

        # Set state: failover active, last notified 35 min ago
        monitor.notification_state["active_issues"]["failover"] = True
        monitor.notification_state["last_notification_time"]["failover"] = (
            datetime.now() - timedelta(minutes=35)
        )
        monitor.notification_state["last_vars"]["failover"] = {
            "node_name": "Primary Pi-hole",
            "time": "12:00:00",
            "date": "2026-04-22",
        }

        with patch.object(monitor, "send_notification", new=AsyncMock()) as mock_notify:
            await monitor.check_and_send_reminders()

        mock_notify.assert_called()
        call_kwargs = mock_notify.call_args
        assert call_kwargs[1].get("is_reminder") is True or (
            len(call_kwargs[0]) >= 3 and call_kwargs[0][2] is True
        )

    @pytest.mark.asyncio
    async def test_sends_fallback_vars_when_no_last_vars(self, monitor, tmp_path):
        """Uses fallback template vars when no last_vars are stored."""
        config = {"repeat": {"enabled": True, "interval": 30}}
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text(json.dumps(config))
        monitor.CONFIG["notify_config_path"] = str(config_path)

        monitor.notification_state["active_issues"]["failover"] = True
        monitor.notification_state["last_notification_time"]["failover"] = (
            datetime.now() - timedelta(minutes=35)
        )
        monitor.notification_state["last_vars"].pop("failover", None)

        with patch.object(monitor, "send_notification", new=AsyncMock()) as mock_notify:
            await monitor.check_and_send_reminders()

        # Should still call send_notification (with generated fallback vars)
        mock_notify.assert_called()

    @pytest.mark.asyncio
    async def test_invalid_config_json_returns_silently(self, monitor, tmp_path):
        """Corrupted config file causes function to return silently."""
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text("not valid json {{")
        monitor.CONFIG["notify_config_path"] = str(config_path)

        with patch.object(monitor, "send_notification", new=AsyncMock()) as mock_notify:
            await monitor.check_and_send_reminders()

        mock_notify.assert_not_called()


# ============================================================================
# get_snooze_status tests
# ============================================================================

class TestGetSnoozeStatus:
    """Tests for the snooze status endpoint."""

    @pytest.mark.asyncio
    async def test_no_config_returns_not_snoozed(self, monitor, tmp_path):
        """When no config file exists, returns snoozed=False."""
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "missing.json")
        result = await monitor.get_snooze_status(api_key="test_api_key")
        assert result["snoozed"] is False
        assert result["until"] is None

    @pytest.mark.asyncio
    async def test_active_snooze_returns_remaining_seconds(self, monitor, tmp_path):
        """Active snooze returns snoozed=True and remaining_seconds > 0."""
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        config = {"snooze": {"enabled": True, "until": future}}
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text(json.dumps(config))
        monitor.CONFIG["notify_config_path"] = str(config_path)

        result = await monitor.get_snooze_status(api_key="test_api_key")

        assert result["snoozed"] is True
        assert result["remaining_seconds"] is not None
        assert result["remaining_seconds"] > 0

    @pytest.mark.asyncio
    async def test_expired_snooze_returns_not_snoozed(self, monitor, tmp_path):
        """Expired snooze (past until) is treated as not active."""
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        config = {"snooze": {"enabled": True, "until": past}}
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text(json.dumps(config))
        monitor.CONFIG["notify_config_path"] = str(config_path)

        result = await monitor.get_snooze_status(api_key="test_api_key")
        assert result["snoozed"] is False


# ============================================================================
# set_snooze tests
# ============================================================================

class TestSetSnooze:
    """Tests for the snooze activation endpoint."""

    @pytest.mark.asyncio
    async def test_set_snooze_default_60_minutes(self, monitor, tmp_path):
        """set_snooze with default duration returns snoozed=True."""
        config_path = tmp_path / "notify_settings.json"
        monitor.CONFIG["notify_config_path"] = str(config_path)

        with patch.object(monitor, "log_event", new=AsyncMock()):
            result = await monitor.set_snooze(
                request=MagicMock(),
                data={"duration": 60},
                api_key="test_api_key",
                _rate_limit=True,
            )

        assert result["snoozed"] is True
        assert result["remaining_seconds"] > 0
        assert config_path.exists()

    @pytest.mark.asyncio
    async def test_set_snooze_saves_to_config(self, monitor, tmp_path):
        """set_snooze persists snooze settings to the config file."""
        config_path = tmp_path / "notify_settings.json"
        monitor.CONFIG["notify_config_path"] = str(config_path)

        with patch.object(monitor, "log_event", new=AsyncMock()):
            await monitor.set_snooze(
                request=MagicMock(),
                data={"duration": 30},
                api_key="test_api_key",
                _rate_limit=True,
            )

        saved = json.loads(config_path.read_text())
        assert saved["snooze"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_set_snooze_zero_duration_raises_400(self, monitor, tmp_path):
        """Duration of 0 raises HTTPException 400."""
        from fastapi import HTTPException

        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify.json")

        with pytest.raises(HTTPException) as exc_info:
            await monitor.set_snooze(
                request=MagicMock(),
                data={"duration": 0},
                api_key="test_api_key",
                _rate_limit=True,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_set_snooze_over_24h_raises_400(self, monitor, tmp_path):
        """Duration > 1440 min (24h) raises HTTPException 400."""
        from fastapi import HTTPException

        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify.json")

        with pytest.raises(HTTPException) as exc_info:
            await monitor.set_snooze(
                request=MagicMock(),
                data={"duration": 1500},
                api_key="test_api_key",
                _rate_limit=True,
            )
        assert exc_info.value.status_code == 400


# ============================================================================
# cancel_snooze tests
# ============================================================================

class TestCancelSnooze:
    """Tests for the snooze cancellation endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_snooze_clears_snooze(self, monitor, tmp_path):
        """cancel_snooze sets enabled=False and clears until."""
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        config = {"snooze": {"enabled": True, "until": future}}
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text(json.dumps(config))
        monitor.CONFIG["notify_config_path"] = str(config_path)

        with patch.object(monitor, "log_event", new=AsyncMock()):
            result = await monitor.cancel_snooze(api_key="test_api_key")

        assert result["snoozed"] is False
        saved = json.loads(config_path.read_text())
        assert saved["snooze"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_cancel_snooze_no_existing_config(self, monitor, tmp_path):
        """cancel_snooze works even when no config file exists yet."""
        config_path = tmp_path / "notify_settings.json"
        monitor.CONFIG["notify_config_path"] = str(config_path)

        with patch.object(monitor, "log_event", new=AsyncMock()):
            result = await monitor.cancel_snooze(api_key="test_api_key")

        assert result["snoozed"] is False


# ============================================================================
# check_who_has_vip tests
# ============================================================================

class TestCheckWhoHasVip:
    """Tests for VIP detection via ARP table."""

    def _make_proc(self, stdout=b""):
        """Create a mock subprocess that returns stdout."""
        proc = AsyncMock()
        proc.returncode = 0
        proc.communicate = AsyncMock(return_value=(stdout, b""))
        return proc

    @pytest.mark.asyncio
    async def test_primary_has_vip(self, monitor):
        """Returns (True, False) when VIP MAC matches primary MAC."""
        vip_out = b"10.10.100.2 dev eth0 lladdr AA:BB:CC:DD:EE:01 REACHABLE"
        primary_out = b"10.10.100.10 dev eth0 lladdr AA:BB:CC:DD:EE:01 REACHABLE"
        secondary_out = b"10.10.100.20 dev eth0 lladdr AA:BB:CC:DD:EE:02 REACHABLE"

        procs = [
            self._make_proc(vip_out),
            self._make_proc(primary_out),
            self._make_proc(secondary_out),
        ]

        sock = MagicMock()
        sock.connect_ex.return_value = 0
        sock.__enter__ = MagicMock(return_value=sock)
        sock.__exit__ = MagicMock(return_value=False)

        with patch("socket.socket", return_value=sock):
            with patch("asyncio.sleep", new=AsyncMock()):
                with patch("asyncio.create_subprocess_exec", side_effect=procs):
                    result = await monitor.check_who_has_vip(
                        "10.10.100.2", "10.10.100.10", "10.10.100.20", max_retries=1
                    )

        assert result == (True, False)

    @pytest.mark.asyncio
    async def test_secondary_has_vip(self, monitor):
        """Returns (False, True) when VIP MAC matches secondary MAC."""
        vip_out = b"10.10.100.2 dev eth0 lladdr AA:BB:CC:DD:EE:02 REACHABLE"
        primary_out = b"10.10.100.10 dev eth0 lladdr AA:BB:CC:DD:EE:01 REACHABLE"
        secondary_out = b"10.10.100.20 dev eth0 lladdr AA:BB:CC:DD:EE:02 REACHABLE"

        procs = [
            self._make_proc(vip_out),
            self._make_proc(primary_out),
            self._make_proc(secondary_out),
        ]

        sock = MagicMock()
        sock.connect_ex.return_value = 0
        sock.__enter__ = MagicMock(return_value=sock)
        sock.__exit__ = MagicMock(return_value=False)

        with patch("socket.socket", return_value=sock):
            with patch("asyncio.sleep", new=AsyncMock()):
                with patch("asyncio.create_subprocess_exec", side_effect=procs):
                    result = await monitor.check_who_has_vip(
                        "10.10.100.2", "10.10.100.10", "10.10.100.20", max_retries=1
                    )

        assert result == (False, True)

    @pytest.mark.asyncio
    async def test_no_vip_arp_entry_returns_false_false(self, monitor):
        """Returns (False, False) when VIP has no ARP entry (both BACKUP)."""
        vip_out = b""  # no ARP entry
        primary_out = b"10.10.100.10 dev eth0 lladdr AA:BB:CC:DD:EE:01 REACHABLE"
        secondary_out = b"10.10.100.20 dev eth0 lladdr AA:BB:CC:DD:EE:02 REACHABLE"

        procs = [
            self._make_proc(vip_out),
            self._make_proc(primary_out),
            self._make_proc(secondary_out),
        ]

        sock = MagicMock()
        sock.connect_ex.return_value = 0
        sock.__enter__ = MagicMock(return_value=sock)
        sock.__exit__ = MagicMock(return_value=False)

        with patch("socket.socket", return_value=sock):
            with patch("asyncio.sleep", new=AsyncMock()):
                with patch("asyncio.create_subprocess_exec", side_effect=procs):
                    result = await monitor.check_who_has_vip(
                        "10.10.100.2", "10.10.100.10", "10.10.100.20", max_retries=1
                    )

        assert result == (False, False)

    @pytest.mark.asyncio
    async def test_exception_returns_false_false(self, monitor):
        """Unexpected exception returns (False, False)."""
        sock = MagicMock()
        sock.connect_ex.return_value = 0
        sock.__enter__ = MagicMock(return_value=sock)
        sock.__exit__ = MagicMock(return_value=False)

        with patch("socket.socket", return_value=sock):
            with patch("asyncio.sleep", new=AsyncMock()):
                with patch(
                    "asyncio.create_subprocess_exec",
                    side_effect=Exception("subprocess failed"),
                ):
                    result = await monitor.check_who_has_vip(
                        "10.10.100.2", "10.10.100.10", "10.10.100.20", max_retries=1
                    )

        assert result == (False, False)
