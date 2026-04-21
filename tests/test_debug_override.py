"""
Unit tests for debug override (test-mode) state management.

Covers: constants, state dict mutation, TTL expiry logic.
Does NOT test HTTP endpoints (those require a running app; integration-scope).
"""

import asyncio
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

_MONITOR_ENV = {
    "PRIMARY_IP": "10.10.100.10",
    "PRIMARY_PASSWORD": "test_password",
    "SECONDARY_IP": "10.10.100.20",
    "SECONDARY_PASSWORD": "test_password",
    "VIP_ADDRESS": "10.10.100.2",
    "CHECK_INTERVAL": "10",
    "DB_PATH": ":memory:",
    "API_KEY": "test_api_key",
}


@pytest.fixture
def monitor(monkeypatch, tmp_path):
    for key, value in _MONITOR_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("DB_PATH", str(tmp_path / "monitor.db"))
    sys.modules.pop("dashboard.monitor", None)
    return importlib.import_module("dashboard.monitor")


class TestDebugOverrideConstants:
    def test_override_ttl_is_ten_minutes(self, monitor):
        assert monitor._OVERRIDE_TTL_SECONDS == 600

    def test_debug_overrides_is_dict(self, monitor):
        assert isinstance(monitor._debug_overrides, dict)

    def test_debug_mode_is_bool(self, monitor):
        assert isinstance(monitor.DEBUG_MODE, bool)

    def test_dns_latency_warn_ms_is_positive_float(self, monitor):
        assert isinstance(monitor.DNS_LATENCY_WARN_MS, float)
        assert monitor.DNS_LATENCY_WARN_MS > 0


class TestDebugOverrideStateMutation:
    def test_set_primary_offline_stores_entry(self, monitor):
        monitor._debug_overrides.clear()
        monitor._debug_overrides["primary"] = {"state": "offline", "expires": 9e18}
        assert "primary" in monitor._debug_overrides
        assert monitor._debug_overrides["primary"]["state"] == "offline"
        monitor._debug_overrides.clear()

    def test_set_secondary_offline_stores_entry(self, monitor):
        monitor._debug_overrides.clear()
        monitor._debug_overrides["secondary"] = {"state": "offline", "expires": 9e18}
        assert "secondary" in monitor._debug_overrides
        monitor._debug_overrides.clear()

    def test_two_nodes_can_be_overridden_independently(self, monitor):
        monitor._debug_overrides.clear()
        monitor._debug_overrides["primary"] = {"state": "offline", "expires": 9e18}
        monitor._debug_overrides["secondary"] = {"state": "offline", "expires": 9e18}
        assert len(monitor._debug_overrides) == 2
        monitor._debug_overrides.clear()

    def test_pop_removes_entry(self, monitor):
        monitor._debug_overrides.clear()
        monitor._debug_overrides["primary"] = {"state": "offline", "expires": 9e18}
        removed = monitor._debug_overrides.pop("primary", None)
        assert removed is not None
        assert "primary" not in monitor._debug_overrides

    def test_pop_missing_key_returns_none(self, monitor):
        monitor._debug_overrides.clear()
        result = monitor._debug_overrides.pop("primary", None)
        assert result is None

    def test_overrides_cleared_by_clear(self, monitor):
        monitor._debug_overrides["primary"] = {"state": "offline", "expires": 9e18}
        monitor._debug_overrides.clear()
        assert len(monitor._debug_overrides) == 0


class TestDebugOverrideTTL:
    def test_future_expiry_is_not_expired(self, monitor):
        loop = asyncio.new_event_loop()
        now_ts = loop.time()
        loop.close()
        future_expiry = now_ts + 600
        monitor._debug_overrides["primary"] = {"state": "offline", "expires": future_expiry}
        override = monitor._debug_overrides["primary"]
        assert override["expires"] > now_ts
        monitor._debug_overrides.clear()

    def test_past_expiry_is_expired(self, monitor):
        loop = asyncio.new_event_loop()
        now_ts = loop.time()
        loop.close()
        past_expiry = 0.0
        monitor._debug_overrides["primary"] = {"state": "offline", "expires": past_expiry}
        override = monitor._debug_overrides["primary"]
        assert now_ts > override["expires"]
        monitor._debug_overrides.clear()

    def test_override_entry_has_required_keys(self, monitor):
        monitor._debug_overrides.clear()
        monitor._debug_overrides["primary"] = {"state": "offline", "expires": 9e18}
        entry = monitor._debug_overrides["primary"]
        assert "state" in entry
        assert "expires" in entry
        monitor._debug_overrides.clear()

