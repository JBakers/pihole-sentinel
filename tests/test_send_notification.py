"""
Tests for send_notification function and related notification logic.

Covers all notification service paths (Telegram, Discord, Pushover, Ntfy, Webhook),
template rendering, snooze logic, event type filtering, and failure handling.
"""

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
# Helpers
# ============================================================================

def make_async_cm(status=200, json_data=None):
    """Create a mock aiohttp response context manager."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data or {})
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm


def make_failing_cm(exc=None):
    """Create a mock aiohttp context manager that raises on enter."""
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=exc or Exception("simulated error"))
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm


BASE_SETTINGS = {
    "events": {"failover": True, "recovery": True, "fault": True},
    "templates": {
        "failover": "Failover: {node_name} is now master at {time}",
        "recovery": "Recovery: {node_name} recovered at {time}",
        "fault": "Fault on {node_name} at {time}",
    },
}

TEMPLATE_VARS = {
    "node_name": "Primary Pi-hole",
    "time": "12:00:00",
    "date": "2026-04-22",
}


def write_config(tmp_path, settings):
    """Write settings dict to notify_settings.json in tmp_path."""
    config_path = tmp_path / "notify_settings.json"
    config_path.write_text(json.dumps(settings))
    return config_path


# ============================================================================
# Config / setup failure tests
# ============================================================================

class TestSendNotificationNoConfig:
    """Tests when the notification config file is absent or unreadable."""

    @pytest.mark.asyncio
    async def test_config_file_missing_does_nothing(self, monitor, tmp_path):
        """When config file does not exist, function returns silently."""
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "nonexistent.json")
        # Should not raise
        await monitor.send_notification("failover", TEMPLATE_VARS)

    @pytest.mark.asyncio
    async def test_invalid_json_logs_error_and_returns(self, monitor, tmp_path):
        """When config file has invalid JSON, error is logged and function returns."""
        config_path = tmp_path / "notify_settings.json"
        config_path.write_text("not valid json {{")
        monitor.CONFIG["notify_config_path"] = str(config_path)

        with patch.object(monitor, "log_event", new=AsyncMock()) as mock_log:
            await monitor.send_notification("failover", TEMPLATE_VARS)
            mock_log.assert_called()

    @pytest.mark.asyncio
    async def test_snoozed_notification_is_skipped(self, monitor, tmp_path):
        """When snooze is active (enabled=True + future until), no HTTP session is created."""
        snooze_until = (datetime.now() + timedelta(hours=1)).isoformat()
        settings = {
            **BASE_SETTINGS,
            "snooze": {"enabled": True, "until": snooze_until},
            "telegram": {"enabled": True, "bot_token": "1234:TOKEN", "chat_id": "999"},
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        with patch.object(monitor, "get_http_session", new=AsyncMock()) as mock_sess:
            await monitor.send_notification("failover", TEMPLATE_VARS)
            mock_sess.assert_not_called()

    @pytest.mark.asyncio
    async def test_disabled_event_type_is_skipped(self, monitor, tmp_path):
        """When event type is disabled, no HTTP session is created."""
        settings = {**BASE_SETTINGS, "events": {"failover": False}}
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        with patch.object(monitor, "get_http_session", new=AsyncMock()) as mock_sess:
            await monitor.send_notification("failover", TEMPLATE_VARS)
            mock_sess.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_template_uses_fallback(self, monitor, tmp_path):
        """When template for event type is missing, a fallback is used without raising."""
        settings = {**BASE_SETTINGS, "templates": {}}  # no templates
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        # No services configured — should complete without error using fallback template
        await monitor.send_notification("failover", TEMPLATE_VARS)


# ============================================================================
# Template security tests
# ============================================================================

class TestSendNotificationTemplateSecurity:
    """Tests for unsafe template placeholder rejection."""

    @pytest.mark.asyncio
    async def test_attribute_access_placeholder_blocked(self, monitor, tmp_path):
        """Template with {var.__class__} is rejected and event is logged."""
        settings = {
            **BASE_SETTINGS,
            "templates": {"failover": "Hello {node_name.__class__}"},
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        with patch.object(monitor, "log_event", new=AsyncMock()) as mock_log:
            await monitor.send_notification("failover", TEMPLATE_VARS)
            mock_log.assert_called()

    @pytest.mark.asyncio
    async def test_index_access_placeholder_blocked(self, monitor, tmp_path):
        """Template with {var[0]} is rejected and event is logged."""
        settings = {
            **BASE_SETTINGS,
            "templates": {"failover": "Hello {node_name[0]}"},
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        with patch.object(monitor, "log_event", new=AsyncMock()) as mock_log:
            await monitor.send_notification("failover", TEMPLATE_VARS)
            mock_log.assert_called()

    @pytest.mark.asyncio
    async def test_format_spec_placeholder_blocked(self, monitor, tmp_path):
        """Template with {var!r} format spec is rejected."""
        settings = {
            **BASE_SETTINGS,
            "templates": {"failover": "Hello {node_name!r}"},
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        with patch.object(monitor, "log_event", new=AsyncMock()) as mock_log:
            await monitor.send_notification("failover", TEMPLATE_VARS)
            mock_log.assert_called()

    @pytest.mark.asyncio
    async def test_unknown_variable_uses_unknown_placeholder(self, monitor, tmp_path):
        """Template referencing unknown var uses [unknown] default."""
        settings = {
            **BASE_SETTINGS,
            "templates": {"failover": "Node: {nonexistent_var}"},
            "telegram": {"enabled": True, "bot_token": "1234:TOKEN", "chat_id": "999"},
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, {"ok": True})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "log_event", new=AsyncMock()):
                await monitor.send_notification("failover", TEMPLATE_VARS)

        call_json = mock_session.post.call_args[1].get("json", {})
        assert "[unknown]" in call_json.get("text", "")


# ============================================================================
# Telegram tests
# ============================================================================

class TestSendNotificationTelegram:
    """Tests for Telegram notification sending."""

    @pytest.mark.asyncio
    async def test_telegram_success(self, monitor, tmp_path):
        """Successful Telegram notification increments sent_count and logs it."""
        settings = {
            **BASE_SETTINGS,
            "telegram": {
                "enabled": True,
                "bot_token": "1234:ABCDEF",
                "chat_id": "-100123456",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, {"ok": True})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "log_event", new=AsyncMock()) as mock_log:
                await monitor.send_notification("failover", TEMPLATE_VARS)

        mock_session.post.assert_called_once()
        call_url = mock_session.post.call_args[0][0]
        assert "api.telegram.org" in call_url
        # Notification sent event must be logged
        logged_types = [c[0][0] for c in mock_log.call_args_list]
        assert "notification" in logged_types

    @pytest.mark.asyncio
    async def test_telegram_failure_non_200(self, monitor, tmp_path):
        """Non-200 Telegram response logs failure but does not raise."""
        settings = {
            **BASE_SETTINGS,
            "telegram": {
                "enabled": True,
                "bot_token": "1234:ABCDEF",
                "chat_id": "-100123456",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(400, {"ok": False})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "log_event", new=AsyncMock()) as mock_log:
                await monitor.send_notification("failover", TEMPLATE_VARS)

        # Warning event about failed services should be logged
        logged_types = [c[0][0] for c in mock_log.call_args_list]
        assert "warning" in logged_types

    @pytest.mark.asyncio
    async def test_telegram_exception_does_not_raise(self, monitor, tmp_path):
        """Exception during Telegram send is caught and function returns normally."""
        settings = {
            **BASE_SETTINGS,
            "telegram": {
                "enabled": True,
                "bot_token": "1234:ABCDEF",
                "chat_id": "-100123456",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        mock_session.post.return_value = make_failing_cm(Exception("Connection refused"))

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "log_event", new=AsyncMock()):
                # Must not raise
                await monitor.send_notification("failover", TEMPLATE_VARS)

    @pytest.mark.asyncio
    async def test_telegram_missing_token_is_skipped(self, monitor, tmp_path):
        """Telegram with empty bot_token is skipped; no HTTP request made."""
        settings = {
            **BASE_SETTINGS,
            "telegram": {"enabled": True, "bot_token": "", "chat_id": "123"},
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            await monitor.send_notification("failover", TEMPLATE_VARS)

        mock_session.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_telegram_missing_chat_id_is_skipped(self, monitor, tmp_path):
        """Telegram with empty chat_id is skipped."""
        settings = {
            **BASE_SETTINGS,
            "telegram": {"enabled": True, "bot_token": "1234:TOKEN", "chat_id": ""},
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            await monitor.send_notification("failover", TEMPLATE_VARS)

        mock_session.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_reminder_adds_reminder_prefix(self, monitor, tmp_path):
        """is_reminder=True prepends REMINDER to the message."""
        settings = {
            **BASE_SETTINGS,
            "telegram": {
                "enabled": True,
                "bot_token": "1234:TOKEN",
                "chat_id": "999",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, {"ok": True})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "log_event", new=AsyncMock()):
                await monitor.send_notification("failover", TEMPLATE_VARS, is_reminder=True)

        call_json = mock_session.post.call_args[1].get("json", {})
        assert "REMINDER" in call_json.get("text", "")


# ============================================================================
# Discord tests
# ============================================================================

class TestSendNotificationDiscord:
    """Tests for Discord webhook notification sending."""

    @pytest.mark.asyncio
    async def test_discord_success_204(self, monitor, tmp_path):
        """Discord webhook with 204 response is treated as success."""
        settings = {
            **BASE_SETTINGS,
            "discord": {
                "enabled": True,
                "webhook_url": "https://discord.com/api/webhooks/123456/token_abc",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(204, {})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "log_event", new=AsyncMock()) as mock_log:
                await monitor.send_notification("failover", TEMPLATE_VARS)

        mock_session.post.assert_called_once()
        logged_types = [c[0][0] for c in mock_log.call_args_list]
        assert "notification" in logged_types

    @pytest.mark.asyncio
    async def test_discord_invalid_webhook_skips(self, monitor, tmp_path):
        """Discord webhook to a private IP is skipped (SSRF protection)."""
        settings = {
            **BASE_SETTINGS,
            "discord": {
                "enabled": True,
                "webhook_url": "http://192.168.1.1/malicious",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            await monitor.send_notification("failover", TEMPLATE_VARS)

        mock_session.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_discord_exception_does_not_raise(self, monitor, tmp_path):
        """Exception during Discord send is caught silently."""
        settings = {
            **BASE_SETTINGS,
            "discord": {
                "enabled": True,
                "webhook_url": "https://discord.com/api/webhooks/123/token",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        mock_session.post.return_value = make_failing_cm(Exception("network error"))

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "log_event", new=AsyncMock()):
                await monitor.send_notification("failover", TEMPLATE_VARS)


# ============================================================================
# Pushover tests
# ============================================================================

class TestSendNotificationPushover:
    """Tests for Pushover notification sending."""

    @pytest.mark.asyncio
    async def test_pushover_success(self, monitor, tmp_path):
        """Successful Pushover notification is sent to pushover.net."""
        settings = {
            **BASE_SETTINGS,
            "pushover": {
                "enabled": True,
                "user_key": "uXXXXXXXXXXXXXXXXXXXX",
                "app_token": "aXXXXXXXXXXXXXXXXXXXX",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, {"status": 1})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "log_event", new=AsyncMock()):
                await monitor.send_notification("failover", TEMPLATE_VARS)

        mock_session.post.assert_called_once()
        call_url = mock_session.post.call_args[0][0]
        assert "pushover.net" in call_url

    @pytest.mark.asyncio
    async def test_pushover_missing_user_key_skips(self, monitor, tmp_path):
        """Pushover with missing user_key is skipped."""
        settings = {
            **BASE_SETTINGS,
            "pushover": {"enabled": True, "user_key": "", "app_token": "aXXX"},
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            await monitor.send_notification("failover", TEMPLATE_VARS)

        mock_session.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_pushover_failure_non_200(self, monitor, tmp_path):
        """Non-200 Pushover response logs a warning."""
        settings = {
            **BASE_SETTINGS,
            "pushover": {
                "enabled": True,
                "user_key": "uXXXXXXXXXXXXXXXXXXXX",
                "app_token": "aXXXXXXXXXXXXXXXXXXXX",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(429, {})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "log_event", new=AsyncMock()) as mock_log:
                await monitor.send_notification("failover", TEMPLATE_VARS)

        logged_types = [c[0][0] for c in mock_log.call_args_list]
        assert "warning" in logged_types


# ============================================================================
# Ntfy tests
# ============================================================================

class TestSendNotificationNtfy:
    """Tests for Ntfy notification sending."""

    @pytest.mark.asyncio
    async def test_ntfy_success(self, monitor, tmp_path):
        """Successful Ntfy notification is sent to ntfy.sh/{topic}."""
        settings = {
            **BASE_SETTINGS,
            "ntfy": {
                "enabled": True,
                "topic": "pihole-sentinel",
                "server": "https://ntfy.sh",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, {})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "log_event", new=AsyncMock()):
                await monitor.send_notification("failover", TEMPLATE_VARS)

        mock_session.post.assert_called_once()
        call_url = mock_session.post.call_args[0][0]
        assert "ntfy.sh/pihole-sentinel" in call_url

    @pytest.mark.asyncio
    async def test_ntfy_invalid_server_skips(self, monitor, tmp_path):
        """Ntfy with a private IP server URL is skipped (SSRF protection)."""
        settings = {
            **BASE_SETTINGS,
            "ntfy": {
                "enabled": True,
                "topic": "alerts",
                "server": "http://10.0.0.1/ntfy",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            await monitor.send_notification("failover", TEMPLATE_VARS)

        mock_session.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_ntfy_missing_topic_skips(self, monitor, tmp_path):
        """Ntfy with empty topic is skipped."""
        settings = {
            **BASE_SETTINGS,
            "ntfy": {"enabled": True, "topic": "", "server": "https://ntfy.sh"},
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            await monitor.send_notification("failover", TEMPLATE_VARS)

        mock_session.post.assert_not_called()


# ============================================================================
# Custom Webhook tests
# ============================================================================

class TestSendNotificationWebhook:
    """Tests for custom webhook notification sending."""

    @pytest.mark.asyncio
    async def test_webhook_success_200(self, monitor, tmp_path):
        """Successful webhook notification with 200 response."""
        settings = {
            **BASE_SETTINGS,
            "webhook": {
                "enabled": True,
                "url": "https://example.com/hooks/pihole",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, {})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "log_event", new=AsyncMock()) as mock_log:
                await monitor.send_notification("failover", TEMPLATE_VARS)

        mock_session.post.assert_called_once()
        logged_types = [c[0][0] for c in mock_log.call_args_list]
        assert "notification" in logged_types

    @pytest.mark.asyncio
    async def test_webhook_202_accepted(self, monitor, tmp_path):
        """Webhook returning 202 Accepted is treated as success."""
        settings = {
            **BASE_SETTINGS,
            "webhook": {
                "enabled": True,
                "url": "https://example.com/hooks/pihole",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(202, {})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "log_event", new=AsyncMock()) as mock_log:
                await monitor.send_notification("failover", TEMPLATE_VARS)

        logged_types = [c[0][0] for c in mock_log.call_args_list]
        assert "notification" in logged_types

    @pytest.mark.asyncio
    async def test_webhook_failure_non_2xx(self, monitor, tmp_path):
        """Non-2xx webhook response logs a warning."""
        settings = {
            **BASE_SETTINGS,
            "webhook": {
                "enabled": True,
                "url": "https://example.com/hooks/pihole",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(500, {})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "log_event", new=AsyncMock()) as mock_log:
                await monitor.send_notification("failover", TEMPLATE_VARS)

        logged_types = [c[0][0] for c in mock_log.call_args_list]
        assert "warning" in logged_types

    @pytest.mark.asyncio
    async def test_webhook_invalid_url_skips(self, monitor, tmp_path):
        """Webhook to a private IP is skipped (SSRF protection)."""
        settings = {
            **BASE_SETTINGS,
            "webhook": {
                "enabled": True,
                "url": "http://169.254.169.254/metadata",  # link-local / metadata service
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            await monitor.send_notification("failover", TEMPLATE_VARS)

        mock_session.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_webhook_payload_contains_event_type(self, monitor, tmp_path):
        """Webhook payload includes event_type and message fields."""
        settings = {
            **BASE_SETTINGS,
            "webhook": {
                "enabled": True,
                "url": "https://example.com/hooks/pihole",
            },
        }
        write_config(tmp_path, settings)
        monitor.CONFIG["notify_config_path"] = str(tmp_path / "notify_settings.json")

        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, {})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "log_event", new=AsyncMock()):
                await monitor.send_notification("failover", TEMPLATE_VARS)

        call_json = mock_session.post.call_args[1].get("json", {})
        assert call_json.get("event_type") == "failover"
        assert "message" in call_json
        assert call_json.get("service") == "pihole-sentinel"
