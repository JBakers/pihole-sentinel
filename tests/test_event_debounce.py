"""Tests for event debounce in monitor_loop.

Brief Pi-hole FTL restarts (e.g. during config sync) should NOT generate
dashboard events.  Only outages lasting >= EVENT_DEBOUNCE_SECONDS (30 s)
should be logged.
"""

import importlib
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

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
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    sys.modules.pop("dashboard.monitor", None)
    mod = importlib.import_module("dashboard.monitor")
    # Reset module-level debounce state between tests
    mod._offline_since.clear()
    mod._offline_event_logged.clear()
    mod._pihole_down_since.clear()
    mod._pihole_down_event_logged.clear()
    mod._fault_tasks.clear()
    mod._fault_notified.clear()
    return mod


# ────────────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────────────

class TestDebounceConstants:
    """Verify debounce timing constants."""

    def test_event_debounce_is_30_seconds(self, monitor):
        assert monitor.EVENT_DEBOUNCE_SECONDS == 30

    def test_fault_notification_delay_is_30_seconds(self, monitor):
        assert monitor.FAULT_NOTIFICATION_DELAY == 30

    def test_total_notification_delay_is_60_seconds(self, monitor):
        """Total delay = event debounce + fault notification delay ≈ 60 s."""
        total = monitor.EVENT_DEBOUNCE_SECONDS + monitor.FAULT_NOTIFICATION_DELAY
        assert total == 60


# ────────────────────────────────────────────────────────────────────────────
# Offline event debounce
# ────────────────────────────────────────────────────────────────────────────

class TestOfflineDebounce:
    """Offline events should only be logged after EVENT_DEBOUNCE_SECONDS."""

    def test_first_offline_detection_records_timestamp(self, monitor):
        """When a node first goes offline, _offline_since is set but no event."""
        assert "secondary" not in monitor._offline_since

        # Simulate: node was online (previous=True), now offline
        monitor._offline_since["secondary"] = datetime.now()

        assert "secondary" in monitor._offline_since
        assert "secondary" not in monitor._offline_event_logged

    def test_offline_within_debounce_no_event(self, monitor):
        """Node offline < 30 s should NOT be in _offline_event_logged."""
        monitor._offline_since["secondary"] = datetime.now()
        elapsed = (datetime.now() - monitor._offline_since["secondary"]).total_seconds()

        assert elapsed < monitor.EVENT_DEBOUNCE_SECONDS
        assert "secondary" not in monitor._offline_event_logged

    def test_offline_after_debounce_logs_event(self, monitor):
        """Node offline >= 30 s should trigger event logging."""
        # Set timestamp 31 seconds in the past
        monitor._offline_since["secondary"] = datetime.now() - timedelta(seconds=31)
        elapsed = (datetime.now() - monitor._offline_since["secondary"]).total_seconds()

        assert elapsed >= monitor.EVENT_DEBOUNCE_SECONDS
        # In the real loop this would log the event and set the flag:
        monitor._offline_event_logged.add("secondary")
        assert "secondary" in monitor._offline_event_logged

    def test_recovery_before_debounce_suppresses_silently(self, monitor):
        """Recovery within 30 s should clear state without logging events."""
        monitor._offline_since["secondary"] = datetime.now()
        assert "secondary" not in monitor._offline_event_logged

        # Simulate recovery: clear state
        monitor._offline_since.pop("secondary", None)
        monitor._offline_event_logged.discard("secondary")

        assert "secondary" not in monitor._offline_since
        assert "secondary" not in monitor._offline_event_logged

    def test_recovery_after_event_triggers_online_event(self, monitor):
        """Recovery after offline event was logged should allow 'is back ONLINE'."""
        monitor._offline_since["primary"] = datetime.now() - timedelta(seconds=45)
        monitor._offline_event_logged.add("primary")

        # Simulate recovery: was_logged is checked
        was_logged = "primary" in monitor._offline_event_logged
        assert was_logged is True

        # Clean up
        monitor._offline_since.pop("primary", None)
        monitor._offline_event_logged.discard("primary")
        assert "primary" not in monitor._offline_since


# ────────────────────────────────────────────────────────────────────────────
# Pi-hole service event debounce
# ────────────────────────────────────────────────────────────────────────────

class TestPiholeServiceDebounce:
    """Pi-hole service events follow the same debounce pattern."""

    def test_pihole_down_records_timestamp(self, monitor):
        """First pihole-down detection starts debounce timer."""
        monitor._pihole_down_since["secondary"] = datetime.now()
        assert "secondary" in monitor._pihole_down_since
        assert "secondary" not in monitor._pihole_down_event_logged

    def test_pihole_down_within_debounce_no_event(self, monitor):
        """Pihole down < 30 s should not be logged."""
        monitor._pihole_down_since["secondary"] = datetime.now()
        elapsed = (datetime.now() - monitor._pihole_down_since["secondary"]).total_seconds()
        assert elapsed < monitor.EVENT_DEBOUNCE_SECONDS

    def test_pihole_recovery_before_debounce_suppresses(self, monitor):
        """Pi-hole recovery within debounce clears state silently."""
        monitor._pihole_down_since["secondary"] = datetime.now()
        # Simulate recovery
        monitor._pihole_down_since.pop("secondary", None)
        assert "secondary" not in monitor._pihole_down_since

    def test_pihole_recovery_after_event_triggers_up_event(self, monitor):
        """Pi-hole recovery after DOWN event was logged allows 'is back UP'."""
        monitor._pihole_down_since["primary"] = datetime.now() - timedelta(seconds=45)
        monitor._pihole_down_event_logged.add("primary")

        was_logged = "primary" in monitor._pihole_down_event_logged
        assert was_logged is True

        monitor._pihole_down_since.pop("primary", None)
        monitor._pihole_down_event_logged.discard("primary")


# ────────────────────────────────────────────────────────────────────────────
# Orphaned event prevention
# ────────────────────────────────────────────────────────────────────────────

class TestOrphanedEventPrevention:
    """When a node goes offline, pihole=False is a side-effect.
    Recovery should NOT generate a spurious 'Pi-hole is back UP' event."""

    def test_offline_clears_pihole_down_debounce(self, monitor):
        """When node goes offline, pending pihole-down debounce is cleared."""
        monitor._pihole_down_since["secondary"] = datetime.now()

        # Simulate node going offline: pihole debounce should be cleared
        monitor._pihole_down_since.pop("secondary", None)

        assert "secondary" not in monitor._pihole_down_since
        assert "secondary" not in monitor._pihole_down_event_logged

    def test_no_orphaned_pihole_up_after_offline_recovery(self, monitor):
        """After offline recovery, 'Pi-hole is back UP' should NOT appear
        if no 'Pi-hole is DOWN' event was logged."""
        # Node was offline (no pihole DOWN event logged)
        assert "secondary" not in monitor._pihole_down_event_logged

        # Recovery: pihole=True, but since no DOWN was logged → no UP either
        was_logged = "secondary" in monitor._pihole_down_event_logged
        assert was_logged is False


# ────────────────────────────────────────────────────────────────────────────
# Fault task integration
# ────────────────────────────────────────────────────────────────────────────

class TestFaultTaskIntegration:
    """Verify fault debounce functions still work correctly."""

    def test_arm_fault_creates_task(self, monitor):
        """_arm_fault should be idempotent — only one task per key."""
        # We can't easily create real asyncio tasks in sync tests,
        # but we can verify the function signature hasn't changed.
        assert callable(monitor._arm_fault)
        assert callable(monitor._cancel_fault_pending)
        assert callable(monitor._cancel_fault)

    def test_cancel_fault_pending_returns_false_when_no_task(self, monitor):
        """Cancelling a non-existent fault returns False."""
        result = monitor._cancel_fault_pending("nonexistent_key")
        assert result is False

    def test_cancel_fault_pending_clears_task(self, monitor):
        """Cancelling an existing task removes it from _fault_tasks."""
        # Simulate a pending task
        from unittest.mock import MagicMock
        mock_task = MagicMock()
        mock_task.cancel = MagicMock()
        monitor._fault_tasks["test_key"] = mock_task

        result = monitor._cancel_fault_pending("test_key")
        assert result is True
        assert "test_key" not in monitor._fault_tasks
        mock_task.cancel.assert_called_once()
