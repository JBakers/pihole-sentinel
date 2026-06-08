"""Integration tests for the N-node (>2) Docker mock environment.

Requires: `make docker-up-nnode` before running.
Run with: `make docker-test-nnode` or
          `pytest tests/test_integration_nnode.py -m integration`

Validates the N-node architecture end-to-end against a 3-node mock setup:
  Mock Pi-hole API (x3) -> Monitor polling -> nodes[] Status API -> History

The environment (docker-compose.test-nnode.yml) runs on a separate subnet and
ports (mocks 8011-8013, monitor 8090) so it coexists with the 2-node env.
"""

import time

import pytest
import requests

# ─────────────────────────────────────────────────────────────────────
# Configuration — matches docker-compose.test-nnode.yml
# ─────────────────────────────────────────────────────────────────────

NODE_URLS = {
    1: "http://localhost:8011",
    2: "http://localhost:8012",
    3: "http://localhost:8013",
}
MONITOR_URL = "http://localhost:8090"
API_KEY = "test-api-key-nnode"
EXPECTED_NODE_COUNT = 3
POLL_INTERVAL = 5  # seconds (CHECK_INTERVAL in docker-compose.test-nnode.yml)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _docker_is_running() -> bool:
    """Check if the N-node Docker test environment is reachable."""
    try:
        r = requests.get(f"{MONITOR_URL}/", timeout=3)
        return r.status_code == 200
    except requests.RequestException:
        return False


def mock_set_state(node_index, state):
    url = NODE_URLS[node_index]
    r = requests.post(f"{url}/mock/set-state", json=state, timeout=5)
    r.raise_for_status()
    return r.json()


def mock_reset(node_index):
    url = NODE_URLS[node_index]
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


def monitor_history(hours=0.25):
    r = requests.get(
        f"{MONITOR_URL}/api/history",
        headers={"X-API-Key": API_KEY},
        params={"hours": hours},
        timeout=5,
    )
    r.raise_for_status()
    return r.json()


def node_by_index(status, index):
    """Return the node dict with the given index from a status response."""
    return next((n for n in status["nodes"] if n["index"] == index), None)


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


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def require_docker():
    """Skip all tests if the N-node Docker environment is not running."""
    if not _docker_is_running():
        pytest.skip(
            "N-node Docker test environment not running "
            "(run 'make docker-up-nnode' or 'docker compose "
            "-f docker-compose.test-nnode.yml up -d' first)"
        )


@pytest.fixture(autouse=True)
def reset_mocks(require_docker):
    """Reset all mocks to a clean state before and after each test."""
    for idx in NODE_URLS:
        mock_reset(idx)
    wait_for_detection(cycles=2)
    yield
    for idx in NODE_URLS:
        mock_reset(idx)


# ─────────────────────────────────────────────────────────────────────
# N1. nodes[] API shape
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestNodeArray:

    def test_status_returns_all_nodes(self):
        """/api/status returns a nodes[] array with every configured node."""
        status = monitor_status()
        assert "nodes" in status, "status response missing 'nodes' array"
        assert len(status["nodes"]) == EXPECTED_NODE_COUNT
        indices = sorted(n["index"] for n in status["nodes"])
        assert indices == [1, 2, 3]

    def test_nodes_have_expected_names(self):
        """Each node carries the name configured in the compose file."""
        status = monitor_status()
        names = {n["index"]: n["name"] for n in status["nodes"]}
        assert names[1] == "Node 1"
        assert names[2] == "Node 2"
        assert names[3] == "Node 3"

    def test_nodes_have_required_fields(self):
        """Every node entry exposes the full per-node status schema."""
        status = monitor_status()
        required = {
            "index",
            "ip",
            "name",
            "state",
            "has_vip",
            "online",
            "pihole",
            "dns",
            "dhcp",
        }
        for node in status["nodes"]:
            missing = required - set(node)
            assert not missing, f"node {node['index']} missing fields: {missing}"

    def test_backward_compat_primary_secondary(self):
        """Legacy primary/secondary mirror nodes[0] and nodes[1]."""
        status = monitor_status()
        assert status["primary"]["name"] == status["nodes"][0]["name"]
        assert status["secondary"]["name"] == status["nodes"][1]["name"]


# ─────────────────────────────────────────────────────────────────────
# N2. Per-node failover detection (third node)
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestThirdNodeFailover:

    def test_node3_offline_detected(self):
        """When node 3 FTL stops, the monitor flags it offline in nodes[]."""
        mock_set_state(3, {"pihole_running": False})
        assert wait_for_condition(
            lambda: node_by_index(monitor_status(), 3)["pihole"] is False
        ), "Monitor did not detect node 3 FTL offline"

    def test_node3_offline_does_not_affect_others(self):
        """A node 3 failure leaves nodes 1 and 2 reporting healthy."""
        mock_set_state(3, {"pihole_running": False})
        wait_for_detection(cycles=3)
        status = monitor_status()
        assert node_by_index(status, 1)["pihole"] is True
        assert node_by_index(status, 2)["pihole"] is True

    def test_node3_recovers(self):
        """After reset, node 3 is detected healthy again."""
        mock_set_state(3, {"pihole_running": False})
        assert wait_for_condition(
            lambda: node_by_index(monitor_status(), 3)["pihole"] is False
        )
        mock_reset(3)
        assert wait_for_condition(
            lambda: node_by_index(monitor_status(), 3)["pihole"] is True
        ), "Monitor did not detect node 3 recovery"


# ─────────────────────────────────────────────────────────────────────
# N3. History endpoint with N nodes
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestNodeHistory:

    def test_history_entries_contain_nodes_array(self):
        """Each history entry exposes a nodes[] array with all nodes."""
        wait_for_detection(cycles=2)
        history = monitor_history(hours=0.25)
        assert isinstance(history, list) and history, "history is empty"
        latest = history[-1]
        assert "nodes" in latest, "history entry missing 'nodes' array"
        indices = sorted(n["index"] for n in latest["nodes"])
        assert indices == [1, 2, 3]
