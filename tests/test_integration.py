"""Integration tests against Docker mock Pi-hole environment.

Requires: `make docker-up` before running.
Run with: `make docker-integration` or `pytest tests/test_integration.py -m integration`

Tests validate the full monitoring pipeline:
  Mock Pi-hole API -> Monitor polling -> Status API -> Event logging

Docker test environment uses EVENT_DEBOUNCE_SECONDS=5 to keep tests fast.
"""

import time
from datetime import datetime

import pytest
import requests

# ─────────────────────────────────────────────────────────────────────
# Configuration — matches docker-compose.test.yml
# ─────────────────────────────────────────────────────────────────────

PRIMARY_URL = "http://localhost:8001"
SECONDARY_URL = "http://localhost:8002"
MONITOR_URL = "http://localhost:8080"
API_KEY = "test-api-key-12345"
POLL_INTERVAL = 5  # seconds (CHECK_INTERVAL in docker-compose)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _docker_is_running() -> bool:
    """Check if the Docker test environment is reachable."""
    try:
        r = requests.get(f"{MONITOR_URL}/", timeout=3)
        return r.status_code == 200
    except requests.RequestException:
        return False


def mock_set_state(node, state):
    url = PRIMARY_URL if node == "primary" else SECONDARY_URL
    r = requests.post(f"{url}/mock/set-state", json=state, timeout=5)
    r.raise_for_status()
    return r.json()


def mock_reset(node):
    url = PRIMARY_URL if node == "primary" else SECONDARY_URL
    r = requests.post(f"{url}/mock/reset", json={}, timeout=5)
    r.raise_for_status()
    return r.json()


def monitor_status():
    r = requests.get(
        f"{MONITOR_URL}/api/status",
        headers={"X-API-Key": API_KEY},
        timeout=5,
    )
    r.raise_for_status()
    return r.json()


def monitor_events(limit=50):
    """Get monitor events (returns the recent_events list)."""
    r = requests.get(
        f"{MONITOR_URL}/api/events",
        headers={"X-API-Key": API_KEY},
        params={"limit": limit},
        timeout=5,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("recent_events", [])


def monitor_history(hours=0.25):
    r = requests.get(
        f"{MONITOR_URL}/api/history",
        headers={"X-API-Key": API_KEY},
        params={"hours": hours},
        timeout=5,
    )
    r.raise_for_status()
    return r.json()


def events_since(since, limit=50):
    """Get monitor events that occurred after a given timestamp."""
    all_events = monitor_events(limit=limit)
    return [e for e in all_events if e["timestamp"] >= since]


def wait_for_condition(check_fn, timeout=30, interval=3):
    """Poll until check_fn() returns True, or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if check_fn():
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def wait_for_detection(cycles=3):
    """Wait for the monitor to complete polling cycles."""
    time.sleep(POLL_INTERVAL * cycles)


def now_ts():
    """Return current timestamp from the monitor's clock (avoids timezone issues)."""
    status = monitor_status()
    return status["timestamp"]


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def require_docker():
    """Skip all tests if Docker environment is not running."""
    if not _docker_is_running():
        pytest.skip("Docker test environment not running (run 'make docker-up' first)")


@pytest.fixture(autouse=True)
def reset_mocks(require_docker):
    """Reset both mocks to clean state before and after each test."""
    mock_reset("primary")
    mock_reset("secondary")
    wait_for_detection(cycles=2)
    yield
    mock_reset("primary")
    mock_reset("secondary")


# ─────────────────────────────────────────────────────────────────────
# T1. Primary Pi-hole failure
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestPrimaryFailure:

    def test_primary_offline_detected(self):
        """When primary FTL stops, monitor detects it as offline."""
        mock_set_state("primary", {"pihole_running": False})
        assert wait_for_condition(
            lambda: monitor_status()["primary"]["pihole"] is False
        ), "Monitor did not detect primary FTL offline"
        assert monitor_status()["secondary"]["pihole"] is True

    def test_primary_failure_logs_event(self):
        """Primary failure creates an event in the timeline."""
        mock_set_state("primary", {"pihole_running": False})
        wait_for_detection(cycles=3)

        events = monitor_events(limit=50)
        descriptions = [e["description"].lower() for e in events]
        assert any("primary" in d and ("down" in d or "offline" in d)
                    for d in descriptions), \
            f"No primary offline event in events: {descriptions[:5]}"


# ─────────────────────────────────────────────────────────────────────
# T2. Secondary Pi-hole failure
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestSecondaryFailure:

    def test_secondary_offline_detected(self):
        """When secondary FTL stops, monitor detects it."""
        mock_set_state("secondary", {"pihole_running": False})
        assert wait_for_condition(
            lambda: monitor_status()["secondary"]["pihole"] is False
        ), "Monitor did not detect secondary FTL offline"
        assert monitor_status()["primary"]["pihole"] is True

    def test_secondary_failure_logs_event(self):
        """Secondary failure creates an event."""
        mock_set_state("secondary", {"pihole_running": False})
        wait_for_detection(cycles=3)

        events = monitor_events(limit=50)
        descriptions = [e["description"].lower() for e in events]
        assert any("secondary" in d and ("down" in d or "offline" in d)
                    for d in descriptions), \
            f"No secondary offline event in events: {descriptions[:5]}"


# ─────────────────────────────────────────────────────────────────────
# T3. DHCP failure on primary
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestDhcpFailurePrimary:

    def test_dhcp_disabled_on_primary_detected(self):
        """When primary has DHCP disabled, monitor sees dhcp=False."""
        mock_set_state("primary", {"dhcp_enabled": False})
        assert wait_for_condition(
            lambda: monitor_status()["primary"]["dhcp"] is False
        ), "Monitor did not detect DHCP disabled on primary"


# ─────────────────────────────────────────────────────────────────────
# T4. DHCP state on secondary
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestDhcpSecondaryState:

    def test_secondary_dhcp_state_reported(self):
        """Secondary DHCP state is correctly reported by monitor."""
        status = monitor_status()
        assert "dhcp" in status["secondary"]


# ─────────────────────────────────────────────────────────────────────
# T5. Stats (queries, blocked, clients)
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestStatsReporting:

    def test_primary_stats_nonzero(self):
        """Primary should report queries > 0 when healthy."""
        status = monitor_status()
        p = status["primary"]
        assert p["queries"] > 0
        assert p["blocked"] > 0
        assert p["clients"] > 0

    def test_secondary_stats_nonzero(self):
        """Secondary should report queries > 0 when healthy."""
        status = monitor_status()
        assert status["secondary"]["queries"] > 0


# ─────────────────────────────────────────────────────────────────────
# T6. VIP detection
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestVipDetection:

    def test_vip_status_present(self):
        """Monitor should report VIP fields in status."""
        status = monitor_status()
        assert "has_vip" in status["primary"]
        assert "has_vip" in status["secondary"]
        assert "vip" in status


# ─────────────────────────────────────────────────────────────────────
# T7. DHCP master/backup consistency
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestDhcpMasterBackup:

    def test_primary_mock_has_dhcp_enabled(self):
        """Primary mock (DHCP_ENABLED=true) starts with DHCP on."""
        r = requests.get(f"{PRIMARY_URL}/mock/state", timeout=5)
        assert r.json()["dhcp_enabled"] is True

    def test_secondary_dhcp_disabled(self):
        """Secondary (DHCP_ENABLED=false) should report DHCP disabled."""
        status = monitor_status()
        assert status["secondary"]["dhcp"] is False


# ─────────────────────────────────────────────────────────────────────
# T8. Failover event logging
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestFailoverEvents:

    def test_failure_and_recovery_events(self):
        """Full failure -> recovery cycle creates both events."""
        mock_set_state("primary", {"pihole_running": False})
        wait_for_detection(cycles=3)

        mock_reset("primary")
        wait_for_detection(cycles=3)

        events = monitor_events(limit=50)
        descriptions = [e["description"].lower() for e in events]

        has_failure = any("down" in d or "offline" in d for d in descriptions)
        has_recovery = any("ok" in d or "running" in d or "online" in d
                          or "back" in d for d in descriptions)

        assert has_failure, f"No failure event: {descriptions[:5]}"
        assert has_recovery, f"No recovery event: {descriptions[:5]}"


# ─────────────────────────────────────────────────────────────────────
# T9. Client discovery and DHCP leases
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestClientDiscovery:

    def test_leases_present(self):
        """Monitor should report DHCP leases from mock Pi-holes."""
        status = monitor_status()
        assert status.get("dhcp_leases", 0) >= 3


# ─────────────────────────────────────────────────────────────────────
# T10. Recovery after failure
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestRecoveryAfterFailure:

    def test_full_recovery(self):
        """After failure + recovery, all systems report healthy."""
        mock_set_state("primary", {"pihole_running": False})
        assert wait_for_condition(
            lambda: monitor_status()["primary"]["pihole"] is False
        ), "Monitor did not detect failure"

        mock_reset("primary")
        assert wait_for_condition(
            lambda: monitor_status()["primary"]["pihole"] is True
        ), "Monitor did not detect recovery"

        status = monitor_status()
        assert status["primary"]["online"] is True
        assert status["secondary"]["online"] is True


# ─────────────────────────────────────────────────────────────────────
# T11b. DNS resolver checks
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestDnsResolution:

    def test_primary_dns_resolving_when_healthy(self):
        """Primary DNS check should be true in healthy mock state."""
        assert wait_for_condition(
            lambda: monitor_status()["primary"]["dns"] is True,
            timeout=20,
            interval=2,
        ), "Monitor did not detect primary DNS as resolving"

    def test_primary_dns_failure_detected(self):
        """When mock DNS is disabled, monitor should report dns=False."""
        mock_set_state("primary", {"dns_working": False})
        assert wait_for_condition(
            lambda: monitor_status()["primary"]["dns"] is False,
            timeout=25,
            interval=2,
        ), "Monitor did not detect primary DNS failure"


# ─────────────────────────────────────────────────────────────────────
# T11. History endpoint
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestHistoryEndpoint:

    def test_history_has_entries(self):
        """History endpoint should return data after polling."""
        history = monitor_history(hours=1)
        assert len(history) > 0

    def test_history_entries_have_fields(self):
        """History entries should contain expected fields."""
        history = monitor_history(hours=1)
        if history:
            entry = history[0]
            for field in ["time", "primary_online", "secondary_online"]:
                assert field in entry, f"Missing field: {field}"
