"""
Tests for monitor.py helper functions.

Covers: collect_node_issues, describe_master_transition, validate_webhook_url,
is_snoozed, should_send_reminder, init_db, log_event, _arm_fault,
_cancel_fault_pending, _cancel_fault.
"""

import asyncio
import importlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
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
# validate_webhook_url tests
# ============================================================================

class TestValidateWebhookUrl:
    """Tests for the SSRF-prevention webhook URL validator."""

    def test_valid_https_public_domain(self, monitor):
        assert monitor.validate_webhook_url("https://discord.com/api/webhooks/123/token") is True

    def test_valid_http_public_domain(self, monitor):
        assert monitor.validate_webhook_url("https://ntfy.sh/my-topic") is True

    def test_private_ip_blocked(self, monitor):
        assert monitor.validate_webhook_url("http://192.168.1.100/hook") is False

    def test_loopback_blocked(self, monitor):
        assert monitor.validate_webhook_url("http://127.0.0.1/hook") is False

    def test_link_local_blocked(self, monitor):
        assert monitor.validate_webhook_url("http://169.254.169.254/metadata") is False

    def test_non_http_scheme_blocked(self, monitor):
        assert monitor.validate_webhook_url("ftp://example.com/hook") is False

    def test_file_scheme_blocked(self, monitor):
        assert monitor.validate_webhook_url("file:///etc/passwd") is False

    def test_empty_url_blocked(self, monitor):
        assert monitor.validate_webhook_url("") is False

    def test_no_hostname_blocked(self, monitor):
        assert monitor.validate_webhook_url("https:///path") is False

    def test_10_dot_network_blocked(self, monitor):
        assert monitor.validate_webhook_url("http://10.0.0.1/hook") is False


# ============================================================================
# is_snoozed tests
# ============================================================================

class TestIsSnoozed:
    """Tests for the snooze-checking helper."""

    def test_not_snoozed_when_no_snooze_key(self, monitor):
        assert monitor.is_snoozed({}) is False

    def test_not_snoozed_when_enabled_false(self, monitor):
        settings = {"snooze": {"enabled": False, "until": "2099-01-01T00:00:00"}}
        assert monitor.is_snoozed(settings) is False

    def test_not_snoozed_when_no_until_key(self, monitor):
        settings = {"snooze": {"enabled": True}}
        assert monitor.is_snoozed(settings) is False

    def test_snoozed_when_until_in_future(self, monitor):
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        settings = {"snooze": {"enabled": True, "until": future}}
        assert monitor.is_snoozed(settings) is True

    def test_not_snoozed_when_until_in_past(self, monitor):
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        settings = {"snooze": {"enabled": True, "until": past}}
        assert monitor.is_snoozed(settings) is False

    def test_invalid_until_value_returns_false(self, monitor):
        settings = {"snooze": {"enabled": True, "until": "not-a-datetime"}}
        assert monitor.is_snoozed(settings) is False


# ============================================================================
# should_send_reminder tests
# ============================================================================

class TestShouldSendReminder:
    """Tests for the repeat-notification reminder logic."""

    def test_no_reminder_when_repeat_disabled(self, monitor):
        settings = {"repeat": {"enabled": False, "interval": 30}}
        assert monitor.should_send_reminder("failover", settings) is False

    def test_no_reminder_when_interval_zero(self, monitor):
        settings = {"repeat": {"enabled": True, "interval": 0}}
        assert monitor.should_send_reminder("failover", settings) is False

    def test_no_reminder_when_issue_not_active(self, monitor):
        settings = {"repeat": {"enabled": True, "interval": 30}}
        monitor.notification_state["active_issues"]["failover"] = False
        assert monitor.should_send_reminder("failover", settings) is False

    def test_no_reminder_when_no_last_notification(self, monitor):
        settings = {"repeat": {"enabled": True, "interval": 30}}
        monitor.notification_state["active_issues"]["failover"] = True
        monitor.notification_state["last_notification_time"].pop("failover", None)
        assert monitor.should_send_reminder("failover", settings) is False

    def test_no_reminder_before_interval(self, monitor):
        settings = {"repeat": {"enabled": True, "interval": 60}}  # 60 min
        monitor.notification_state["active_issues"]["failover"] = True
        monitor.notification_state["last_notification_time"]["failover"] = (
            datetime.now() - timedelta(minutes=30)  # only 30 min ago
        )
        assert monitor.should_send_reminder("failover", settings) is False

    def test_reminder_after_interval(self, monitor):
        settings = {"repeat": {"enabled": True, "interval": 30}}  # 30 min
        monitor.notification_state["active_issues"]["failover"] = True
        monitor.notification_state["last_notification_time"]["failover"] = (
            datetime.now() - timedelta(minutes=35)  # 35 min ago > 30 min interval
        )
        assert monitor.should_send_reminder("failover", settings) is True


# ============================================================================
# collect_node_issues tests
# ============================================================================

class TestCollectNodeIssues:
    """Tests for the node health issue collector."""

    def test_offline_host_returns_single_issue(self, monitor):
        node_data = {"online": False, "pihole": False}
        issues = monitor.collect_node_issues("Primary", node_data, dns_ok=False)
        assert len(issues) == 1
        assert "offline" in issues[0].lower()

    def test_online_healthy_node_no_issues(self, monitor):
        node_data = {"online": True, "pihole": True}
        issues = monitor.collect_node_issues("Primary", node_data, dns_ok=True)
        assert issues == []

    def test_pihole_service_down_adds_issue(self, monitor):
        node_data = {"online": True, "pihole": False}
        issues = monitor.collect_node_issues("Primary", node_data, dns_ok=True)
        assert len(issues) == 1
        assert "Pi-hole service" in issues[0]

    def test_dns_failing_adds_issue(self, monitor):
        node_data = {"online": True, "pihole": True}
        issues = monitor.collect_node_issues("Primary", node_data, dns_ok=False)
        assert len(issues) == 1
        assert "DNS" in issues[0]

    def test_both_service_and_dns_failing(self, monitor):
        node_data = {"online": True, "pihole": False}
        issues = monitor.collect_node_issues("Primary", node_data, dns_ok=False)
        assert len(issues) == 2

    def test_node_label_appears_in_issue(self, monitor):
        node_data = {"online": True, "pihole": False}
        issues = monitor.collect_node_issues("Secondary", node_data, dns_ok=True)
        assert "Secondary" in issues[0]


# ============================================================================
# describe_master_transition tests
# ============================================================================

class TestDescribeMasterTransition:
    """Tests for failover/recovery classification logic."""

    def _make_data(self, online=True, pihole=True):
        return {"online": online, "pihole": pihole}

    def test_secondary_becomes_master_with_primary_issues_is_failover(self, monitor):
        event, reason = monitor.describe_master_transition(
            previous_master="primary",
            current_master="secondary",
            primary_data=self._make_data(online=False),
            secondary_data=self._make_data(online=True),
            primary_dns=False,
            secondary_dns=True,
            previous_primary_online=None,
            previous_primary_pihole=None,
            previous_primary_dns=None,
        )
        assert event == "failover"
        assert "offline" in reason.lower()

    def test_secondary_becomes_master_no_primary_issues_is_failover(self, monitor):
        """No detectable primary issues → still failover (keepalived decision)."""
        event, reason = monitor.describe_master_transition(
            previous_master="primary",
            current_master="secondary",
            primary_data=self._make_data(online=True, pihole=True),
            secondary_data=self._make_data(online=True),
            primary_dns=True,
            secondary_dns=True,
            previous_primary_online=None,
            previous_primary_pihole=None,
            previous_primary_dns=None,
        )
        assert event == "failover"

    def test_primary_regains_vip_after_failover_is_recovery(self, monitor):
        """Primary regains VIP after being secondary → recovery."""
        event, reason = monitor.describe_master_transition(
            previous_master="secondary",
            current_master="primary",
            primary_data=self._make_data(online=True, pihole=True),
            secondary_data=self._make_data(online=True),
            primary_dns=True,
            secondary_dns=True,
            previous_primary_online=False,
            previous_primary_pihole=False,
            previous_primary_dns=False,
        )
        assert event == "recovery"
        assert reason  # must have explanation

    def test_recovery_with_host_back_online(self, monitor):
        """Recovery reason includes 'back online' when host was previously offline."""
        event, reason = monitor.describe_master_transition(
            previous_master="secondary",
            current_master="primary",
            primary_data=self._make_data(online=True, pihole=True),
            secondary_data=self._make_data(online=True),
            primary_dns=True,
            secondary_dns=True,
            previous_primary_online=False,
            previous_primary_pihole=None,
            previous_primary_dns=None,
        )
        assert event == "recovery"
        assert "online" in reason.lower()

    def test_recovery_with_service_restored(self, monitor):
        """Recovery reason mentions Pi-hole service when it was previously down."""
        event, reason = monitor.describe_master_transition(
            previous_master="secondary",
            current_master="primary",
            primary_data=self._make_data(online=True, pihole=True),
            secondary_data=self._make_data(online=True),
            primary_dns=True,
            secondary_dns=True,
            previous_primary_online=True,
            previous_primary_pihole=False,
            previous_primary_dns=None,
        )
        assert event == "recovery"
        assert "service" in reason.lower() or "pi-hole" in reason.lower()

    def test_secondary_has_issues_while_primary_regains_is_failover(self, monitor):
        """If secondary has issues when primary regains, it's still classified as failover."""
        event, reason = monitor.describe_master_transition(
            previous_master="secondary",
            current_master="primary",
            primary_data=self._make_data(online=True),
            secondary_data=self._make_data(online=False),
            primary_dns=True,
            secondary_dns=False,
            previous_primary_online=None,
            previous_primary_pihole=None,
            previous_primary_dns=None,
        )
        assert event == "failover"

    def test_unrelated_master_change_is_failover(self, monitor):
        """Unknown transition is classified as failover with generic reason."""
        event, reason = monitor.describe_master_transition(
            previous_master=None,
            current_master="primary",
            primary_data=self._make_data(online=True),
            secondary_data=self._make_data(online=True),
            primary_dns=True,
            secondary_dns=True,
            previous_primary_online=None,
            previous_primary_pihole=None,
            previous_primary_dns=None,
        )
        assert event == "failover"


# ============================================================================
# init_db and log_event tests
# ============================================================================

class TestInitDb:
    """Tests for database initialisation."""

    @pytest.mark.asyncio
    async def test_creates_status_history_table(self, monitor, tmp_path):
        """init_db creates the status_history table."""
        db_path = str(tmp_path / "monitor.db")
        monitor.CONFIG["db_path"] = db_path

        await monitor.init_db()

        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='status_history'"
            )
            row = await cursor.fetchone()
        assert row is not None

    @pytest.mark.asyncio
    async def test_creates_events_table(self, monitor, tmp_path):
        """init_db creates the events table."""
        db_path = str(tmp_path / "monitor.db")
        monitor.CONFIG["db_path"] = db_path

        await monitor.init_db()

        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
            )
            row = await cursor.fetchone()
        assert row is not None

    @pytest.mark.asyncio
    async def test_idempotent_multiple_calls(self, monitor, tmp_path):
        """Calling init_db twice does not raise an error."""
        db_path = str(tmp_path / "monitor.db")
        monitor.CONFIG["db_path"] = db_path

        await monitor.init_db()
        await monitor.init_db()  # must not raise


class TestLogEvent:
    """Tests for the log_event helper."""

    @pytest.mark.asyncio
    async def test_inserts_event_row(self, monitor, tmp_path):
        """log_event inserts a row into the events table."""
        db_path = str(tmp_path / "monitor.db")
        monitor.CONFIG["db_path"] = db_path

        await monitor.init_db()
        await monitor.log_event("test_event", "Test message")

        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute("SELECT event_type, message FROM events")
            row = await cursor.fetchone()

        assert row[0] == "test_event"
        assert row[1] == "Test message"

    @pytest.mark.asyncio
    async def test_multiple_events_stored(self, monitor, tmp_path):
        """Multiple calls to log_event all produce separate rows."""
        db_path = str(tmp_path / "monitor.db")
        monitor.CONFIG["db_path"] = db_path

        await monitor.init_db()
        await monitor.log_event("failover", "Failover detected")
        await monitor.log_event("recovery", "Recovery complete")

        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM events")
            count = (await cursor.fetchone())[0]

        assert count == 2


# ============================================================================
# Fault debounce helpers tests
# ============================================================================

class TestFaultDebounceHelpers:
    """Tests for _arm_fault, _cancel_fault_pending, and _cancel_fault."""

    @pytest.mark.asyncio
    async def test_arm_fault_creates_task(self, monitor):
        """_arm_fault creates a background asyncio task."""
        monitor._fault_tasks.clear()
        monitor._fault_notified.discard("primary")

        template_vars = {"node_name": "Primary"}

        with patch.object(monitor, "send_notification", new=AsyncMock()):
            with patch("asyncio.sleep", new=AsyncMock()):
                monitor._arm_fault("primary", template_vars)

        assert "primary" in monitor._fault_tasks
        # Clean up the task
        monitor._fault_tasks["primary"].cancel()

    @pytest.mark.asyncio
    async def test_arm_fault_idempotent(self, monitor):
        """Calling _arm_fault twice for the same key creates only one task."""
        monitor._fault_tasks.clear()
        template_vars = {"node_name": "Primary"}

        with patch.object(monitor, "send_notification", new=AsyncMock()):
            with patch("asyncio.sleep", new=AsyncMock()):
                monitor._arm_fault("primary", template_vars)
                first_task = monitor._fault_tasks.get("primary")
                monitor._arm_fault("primary", template_vars)  # second call

        assert monitor._fault_tasks.get("primary") is first_task  # same task object
        first_task.cancel()

    @pytest.mark.asyncio
    async def test_cancel_fault_pending_returns_true(self, monitor):
        """_cancel_fault_pending returns True when a pending task is cancelled."""
        monitor._fault_tasks.clear()

        async def dummy():
            await asyncio.sleep(9999)

        task = asyncio.create_task(dummy())
        monitor._fault_tasks["primary"] = task

        result = monitor._cancel_fault_pending("primary")

        assert result is True
        assert "primary" not in monitor._fault_tasks

    @pytest.mark.asyncio
    async def test_cancel_fault_pending_returns_false_when_no_task(self, monitor):
        """_cancel_fault_pending returns False when no task exists."""
        monitor._fault_tasks.pop("primary", None)

        result = monitor._cancel_fault_pending("primary")

        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_fault_sends_recovery_when_notification_was_sent(self, monitor):
        """_cancel_fault sends recovery notification when fault was already notified."""
        monitor._fault_tasks.pop("primary", None)
        monitor._fault_notified.add("primary")  # notification was sent

        recovery_vars = {"node_name": "Primary"}

        with patch.object(monitor, "send_notification", new=AsyncMock()) as mock_notify:
            await monitor._cancel_fault("primary", recovery_vars)

        mock_notify.assert_called_once_with("recovery", recovery_vars)
        assert "primary" not in monitor._fault_notified

    @pytest.mark.asyncio
    async def test_cancel_fault_no_recovery_when_task_still_pending(self, monitor):
        """_cancel_fault skips recovery notification when fault task was pending (< 30s)."""
        monitor._fault_notified.discard("primary")

        async def dummy():
            await asyncio.sleep(9999)

        task = asyncio.create_task(dummy())
        monitor._fault_tasks["primary"] = task

        with patch.object(monitor, "send_notification", new=AsyncMock()) as mock_notify:
            await monitor._cancel_fault("primary", {})

        mock_notify.assert_not_called()
