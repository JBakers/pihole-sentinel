"""
Tests for check_for_updates endpoint and _is_newer_version helper.

Covers GitHub API interaction, caching logic, HTTP error handling,
timeout handling, and version comparison edge cases.
"""

import asyncio
import importlib
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


def fresh_cache():
    """Return an empty (un-populated) update cache."""
    return {
        "last_check": None,
        "latest_version": None,
        "release_url": None,
        "check_interval": 21600,
    }


GITHUB_RELEASE = {
    "tag_name": "v0.19.0",
    "html_url": "https://github.com/JBakers/pihole-sentinel/releases/tag/v0.19.0",
}


# ============================================================================
# _is_newer_version tests
# ============================================================================

class TestIsNewerVersion:
    """Unit tests for the _is_newer_version helper."""

    def test_newer_patch_version(self, monitor):
        assert monitor._is_newer_version("0.18.6", "0.18.5") is True

    def test_newer_minor_version(self, monitor):
        assert monitor._is_newer_version("0.19.0", "0.18.5") is True

    def test_newer_major_version(self, monitor):
        assert monitor._is_newer_version("1.0.0", "0.18.5") is True

    def test_same_version_no_update(self, monitor):
        assert monitor._is_newer_version("0.18.5", "0.18.5") is False

    def test_older_version_no_update(self, monitor):
        assert monitor._is_newer_version("0.17.0", "0.18.5") is False

    def test_v_prefix_stripped(self, monitor):
        assert monitor._is_newer_version("v0.19.0", "0.18.5") is True

    def test_empty_latest_returns_false(self, monitor):
        assert monitor._is_newer_version("", "0.18.5") is False

    def test_none_latest_returns_false(self, monitor):
        assert monitor._is_newer_version(None, "0.18.5") is False

    def test_unknown_current_returns_false(self, monitor):
        assert monitor._is_newer_version("0.19.0", "unknown") is False

    def test_empty_current_returns_false(self, monitor):
        assert monitor._is_newer_version("0.19.0", "") is False

    def test_pre_release_vs_stable(self, monitor):
        # A stable 0.19.0 is newer than 0.18.5-beta.1
        assert monitor._is_newer_version("0.19.0", "0.18.5-beta.1") is True


# ============================================================================
# check_for_updates tests
# ============================================================================

class TestCheckForUpdates:
    """Tests for the check_for_updates API handler."""

    @pytest.mark.asyncio
    async def test_returns_update_available(self, monitor):
        """When GitHub returns a newer version, update_available is True."""
        monitor._update_cache = fresh_cache()

        mock_session = MagicMock()
        mock_session.get.return_value = make_async_cm(200, GITHUB_RELEASE)

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "get_version", new=AsyncMock(return_value={"version": "0.18.5"})):
                result = await monitor.check_for_updates()

        assert result["latest_version"] == "0.19.0"
        assert result["current_version"] == "0.18.5"
        assert result["update_available"] is True
        assert result.get("cached") is False

    @pytest.mark.asyncio
    async def test_no_update_when_versions_match(self, monitor):
        """When GitHub version equals current version, update_available is False."""
        monitor._update_cache = fresh_cache()

        mock_session = MagicMock()
        mock_session.get.return_value = make_async_cm(200, {
            "tag_name": "v0.18.5",
            "html_url": "https://github.com/...",
        })

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "get_version", new=AsyncMock(return_value={"version": "0.18.5"})):
                result = await monitor.check_for_updates()

        assert result["update_available"] is False
        assert result["latest_version"] == "0.18.5"

    @pytest.mark.asyncio
    async def test_returns_cached_within_interval(self, monitor):
        """When cache is recent (within check_interval), cached result is returned."""
        monitor._update_cache = {
            "last_check": datetime.now() - timedelta(hours=1),
            "latest_version": "0.19.0",
            "release_url": "https://github.com/...",
            "check_interval": 21600,  # 6 hours
        }

        with patch.object(monitor, "get_version", new=AsyncMock(return_value={"version": "0.18.5"})):
            with patch.object(monitor, "get_http_session", new=AsyncMock()) as mock_sess:
                result = await monitor.check_for_updates()
                mock_sess.assert_not_called()

        assert result["cached"] is True
        assert result["latest_version"] == "0.19.0"

    @pytest.mark.asyncio
    async def test_refreshes_cache_after_interval(self, monitor):
        """When cache is stale (past check_interval), a fresh GitHub request is made."""
        monitor._update_cache = {
            "last_check": datetime.now() - timedelta(hours=7),  # stale
            "latest_version": "0.18.5",
            "release_url": None,
            "check_interval": 21600,
        }

        mock_session = MagicMock()
        mock_session.get.return_value = make_async_cm(200, GITHUB_RELEASE)

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "get_version", new=AsyncMock(return_value={"version": "0.18.5"})):
                result = await monitor.check_for_updates()

        mock_session.get.assert_called_once()
        assert result.get("cached") is False

    @pytest.mark.asyncio
    async def test_github_404_no_releases(self, monitor):
        """GitHub 404 means no releases yet; update_available is False."""
        monitor._update_cache = fresh_cache()

        mock_session = MagicMock()
        mock_session.get.return_value = make_async_cm(404, {})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "get_version", new=AsyncMock(return_value={"version": "0.18.5"})):
                result = await monitor.check_for_updates()

        assert result["update_available"] is False
        assert "No releases" in result.get("message", "")

    @pytest.mark.asyncio
    async def test_github_403_rate_limited(self, monitor):
        """GitHub 403 (rate limited) returns update_available=False with message."""
        monitor._update_cache = fresh_cache()

        mock_session = MagicMock()
        mock_session.get.return_value = make_async_cm(403, {})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "get_version", new=AsyncMock(return_value={"version": "0.18.5"})):
                result = await monitor.check_for_updates()

        assert result["update_available"] is False
        assert "rate" in result.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_github_500_server_error(self, monitor):
        """GitHub 500 returns update_available=False with error field."""
        monitor._update_cache = fresh_cache()

        mock_session = MagicMock()
        mock_session.get.return_value = make_async_cm(500, {})

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "get_version", new=AsyncMock(return_value={"version": "0.18.5"})):
                result = await monitor.check_for_updates()

        assert result["update_available"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self, monitor):
        """asyncio.TimeoutError during GitHub call returns error response."""
        monitor._update_cache = fresh_cache()

        timeout_cm = MagicMock()
        timeout_cm.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        timeout_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get.return_value = timeout_cm

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "get_version", new=AsyncMock(return_value={"version": "0.18.5"})):
                result = await monitor.check_for_updates()

        assert result["update_available"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_generic_exception_returns_error(self, monitor):
        """Generic exception during GitHub call returns error response."""
        monitor._update_cache = fresh_cache()

        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("DNS resolution failed")

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "get_version", new=AsyncMock(return_value={"version": "0.18.5"})):
                result = await monitor.check_for_updates()

        assert result["update_available"] is False
        assert "error" in result
        assert "DNS resolution failed" in result["error"]

    @pytest.mark.asyncio
    async def test_cache_is_populated_after_successful_call(self, monitor):
        """After a successful GitHub call, the cache is updated for next requests."""
        monitor._update_cache = fresh_cache()

        mock_session = MagicMock()
        mock_session.get.return_value = make_async_cm(200, GITHUB_RELEASE)

        with patch.object(monitor, "get_http_session", new=AsyncMock(return_value=mock_session)):
            with patch.object(monitor, "get_version", new=AsyncMock(return_value={"version": "0.18.5"})):
                await monitor.check_for_updates()

        assert monitor._update_cache["latest_version"] == "0.19.0"
        assert monitor._update_cache["last_check"] is not None
