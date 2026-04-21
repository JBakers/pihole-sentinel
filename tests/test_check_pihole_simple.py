"""
Tests for check_pihole_simple function.

Covers TCP connectivity, Pi-hole API authentication, stats retrieval,
DHCP configuration queries, lease counting, and logout handling.
"""

import importlib
import socket
import sys
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


def make_online_socket():
    """Return a mock socket that reports the host as online (connect_ex == 0)."""
    sock = MagicMock()
    sock.connect_ex.return_value = 0
    sock.__enter__ = MagicMock(return_value=sock)
    sock.__exit__ = MagicMock(return_value=False)
    return sock


def make_offline_socket():
    """Return a mock socket that reports the host as offline."""
    sock = MagicMock()
    sock.connect_ex.return_value = 111  # ECONNREFUSED
    sock.__enter__ = MagicMock(return_value=sock)
    sock.__exit__ = MagicMock(return_value=False)
    return sock


AUTH_OK = {"session": {"valid": True, "sid": "test-sid-abc123"}}
AUTH_FAIL = {"session": {"valid": False, "sid": None}}
STATS_OK = {"queries": {"total": 500, "blocked": 50}, "clients": {"total": 10}}
DHCP_ENABLED = {"config": {"dhcp": {"active": True}}}
DHCP_DISABLED = {"config": {"dhcp": {"active": False}}}
LEASES_TWO = {"leases": [{"mac": "aa:bb:cc:dd:ee:01"}, {"mac": "aa:bb:cc:dd:ee:02"}]}
LEASES_EMPTY = {"leases": []}


# ============================================================================
# Offline / connectivity failure tests
# ============================================================================

class TestCheckPiholeSimpleOffline:
    """Tests covering host-offline and connection error paths."""

    @pytest.mark.asyncio
    async def test_socket_connection_refused(self, monitor):
        """When TCP connection is refused, result is fully offline."""
        with patch("socket.socket", return_value=make_offline_socket()):
            result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["online"] is False
        assert result["pihole"] is False
        assert result["queries"] == 0
        assert result["blocked"] == 0
        assert result["clients"] == 0
        assert result["dhcp_leases"] == 0
        assert result["dhcp_enabled"] is None

    @pytest.mark.asyncio
    async def test_socket_exception_returns_offline(self, monitor):
        """When socket() raises an exception, result is offline."""
        with patch("socket.socket", side_effect=OSError("Network unreachable")):
            result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["online"] is False
        assert result["pihole"] is False


# ============================================================================
# Auth failure tests (host online but auth fails)
# ============================================================================

class TestCheckPiholeSimpleAuthFailure:
    """Tests covering authentication failure paths."""

    @pytest.mark.asyncio
    async def test_auth_returns_no_sid(self, monitor):
        """When auth response has no SID, pihole is False but online is True."""
        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, AUTH_FAIL)

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "wrongpass")

        assert result["online"] is True
        assert result["pihole"] is False

    @pytest.mark.asyncio
    async def test_auth_non_200_response(self, monitor):
        """When auth returns HTTP 401, pihole is False."""
        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(401, {})

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["online"] is True
        assert result["pihole"] is False

    @pytest.mark.asyncio
    async def test_auth_post_raises_exception(self, monitor):
        """When auth POST raises an exception, pihole is False."""
        mock_session = MagicMock()
        mock_session.post.return_value = make_failing_cm(Exception("connection error"))

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["online"] is True
        assert result["pihole"] is False

    @pytest.mark.asyncio
    async def test_auth_empty_session_object(self, monitor):
        """When auth response has no session key, pihole is False."""
        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, {})  # missing 'session'

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["pihole"] is False


# ============================================================================
# Full success tests
# ============================================================================

class TestCheckPiholeSimpleSuccess:
    """Tests covering successful full check scenarios."""

    @pytest.mark.asyncio
    async def test_full_success_returns_all_stats(self, monitor):
        """Successful check returns all stats from the Pi-hole API."""
        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, AUTH_OK)
        mock_session.get.side_effect = [
            make_async_cm(200, STATS_OK),
            make_async_cm(200, DHCP_ENABLED),
            make_async_cm(200, LEASES_TWO),
        ]
        mock_session.delete.return_value = make_async_cm(200, {})

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["online"] is True
        assert result["pihole"] is True
        assert result["queries"] == 500
        assert result["blocked"] == 50
        assert result["clients"] == 10
        assert result["dhcp_enabled"] is True
        assert result["dhcp_leases"] == 2

    @pytest.mark.asyncio
    async def test_dhcp_disabled(self, monitor):
        """DHCP disabled is correctly returned."""
        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, AUTH_OK)
        mock_session.get.side_effect = [
            make_async_cm(200, STATS_OK),
            make_async_cm(200, DHCP_DISABLED),
            make_async_cm(200, LEASES_EMPTY),
        ]
        mock_session.delete.return_value = make_async_cm(200, {})

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["dhcp_enabled"] is False
        assert result["dhcp_leases"] == 0

    @pytest.mark.asyncio
    async def test_zero_stats_values(self, monitor):
        """Zero query counts are handled correctly."""
        stats_zero = {"queries": {"total": 0, "blocked": 0}, "clients": {"total": 0}}
        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, AUTH_OK)
        mock_session.get.side_effect = [
            make_async_cm(200, stats_zero),
            make_async_cm(200, DHCP_DISABLED),
            make_async_cm(200, LEASES_EMPTY),
        ]
        mock_session.delete.return_value = make_async_cm(200, {})

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["pihole"] is True
        assert result["queries"] == 0
        assert result["clients"] == 0


# ============================================================================
# Stats API failure tests
# ============================================================================

class TestCheckPiholeSimpleStatsFailure:
    """Tests covering stats API failure paths."""

    @pytest.mark.asyncio
    async def test_stats_non_200_sets_pihole_false(self, monitor):
        """When stats API returns non-200, pihole is False."""
        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, AUTH_OK)
        mock_session.get.return_value = make_async_cm(503, {})
        mock_session.delete.return_value = make_async_cm(200, {})

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["online"] is True
        assert result["pihole"] is False

    @pytest.mark.asyncio
    async def test_stats_exception_sets_pihole_false(self, monitor):
        """When stats GET raises an exception, pihole is False."""
        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, AUTH_OK)
        mock_session.get.return_value = make_failing_cm(Exception("timeout"))
        mock_session.delete.return_value = make_async_cm(200, {})

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["pihole"] is False


# ============================================================================
# DHCP API failure tests
# ============================================================================

class TestCheckPiholeSimpleDhcpFailure:
    """Tests covering DHCP API failure paths."""

    @pytest.mark.asyncio
    async def test_dhcp_non_200_returns_none(self, monitor):
        """When DHCP config API returns non-200, dhcp_enabled is None."""
        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, AUTH_OK)
        mock_session.get.side_effect = [
            make_async_cm(200, STATS_OK),
            make_async_cm(403, {}),       # DHCP endpoint fails
            make_async_cm(200, LEASES_EMPTY),
        ]
        mock_session.delete.return_value = make_async_cm(200, {})

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["pihole"] is True
        assert result["dhcp_enabled"] is None

    @pytest.mark.asyncio
    async def test_dhcp_exception_returns_none(self, monitor):
        """When DHCP config API raises an exception, dhcp_enabled is None."""
        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, AUTH_OK)
        mock_session.get.side_effect = [
            make_async_cm(200, STATS_OK),
            make_failing_cm(Exception("DHCP timeout")),
            make_async_cm(200, LEASES_EMPTY),
        ]
        mock_session.delete.return_value = make_async_cm(200, {})

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["dhcp_enabled"] is None


# ============================================================================
# Leases API failure tests
# ============================================================================

class TestCheckPiholeSimpleLeasesFailure:
    """Tests covering DHCP lease count failure paths."""

    @pytest.mark.asyncio
    async def test_leases_non_200_returns_zero(self, monitor):
        """When leases API returns non-200, dhcp_leases defaults to 0."""
        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, AUTH_OK)
        mock_session.get.side_effect = [
            make_async_cm(200, STATS_OK),
            make_async_cm(200, DHCP_ENABLED),
            make_async_cm(500, {}),  # leases endpoint fails
        ]
        mock_session.delete.return_value = make_async_cm(200, {})

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["dhcp_leases"] == 0

    @pytest.mark.asyncio
    async def test_leases_none_value_returns_zero(self, monitor):
        """When leases API returns null for leases, dhcp_leases is 0."""
        leases_null = {"leases": None}
        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, AUTH_OK)
        mock_session.get.side_effect = [
            make_async_cm(200, STATS_OK),
            make_async_cm(200, DHCP_ENABLED),
            make_async_cm(200, leases_null),
        ]
        mock_session.delete.return_value = make_async_cm(200, {})

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["dhcp_leases"] == 0

    @pytest.mark.asyncio
    async def test_leases_exception_returns_zero(self, monitor):
        """When leases API raises an exception, dhcp_leases is 0."""
        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, AUTH_OK)
        mock_session.get.side_effect = [
            make_async_cm(200, STATS_OK),
            make_async_cm(200, DHCP_ENABLED),
            make_failing_cm(Exception("leases timeout")),
        ]
        mock_session.delete.return_value = make_async_cm(200, {})

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["dhcp_leases"] == 0


# ============================================================================
# Logout / cleanup tests
# ============================================================================

class TestCheckPiholeSimpleLogout:
    """Tests covering logout/cleanup at the end of check."""

    @pytest.mark.asyncio
    async def test_logout_failure_does_not_affect_result(self, monitor):
        """Exception during logout is silently ignored; result is still valid."""
        mock_session = MagicMock()
        mock_session.post.return_value = make_async_cm(200, AUTH_OK)
        mock_session.get.side_effect = [
            make_async_cm(200, STATS_OK),
            make_async_cm(200, DHCP_DISABLED),
            make_async_cm(200, LEASES_EMPTY),
        ]
        mock_session.delete.return_value = make_failing_cm(Exception("logout failed"))

        with patch("socket.socket", return_value=make_online_socket()):
            with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
                result = await monitor.check_pihole_simple("10.10.100.10", "pass")

        assert result["pihole"] is True
        assert result["online"] is True
