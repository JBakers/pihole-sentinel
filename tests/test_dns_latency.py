"""
Unit tests for check_dns() — DNS latency health check.

Covers: return type, success path, failure paths, timeout, OS errors.
"""

import asyncio
import importlib
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

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


class TestCheckDnsReturnType:
    def test_check_dns_is_coroutine(self, monitor):
        import inspect
        assert inspect.iscoroutinefunction(monitor.check_dns)

    @pytest.mark.asyncio
    async def test_returns_tuple_of_two_elements(self, monitor):
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"1.2.3.4\n", b""))
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await monitor.check_dns("10.10.100.10")
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestCheckDnsSuccess:
    @pytest.mark.asyncio
    async def test_valid_response_returns_true_and_float(self, monitor):
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"1.2.3.4\n", b""))
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            ok, latency = await monitor.check_dns("10.10.100.10")
        assert ok is True
        assert isinstance(latency, float)
        assert latency >= 0

    @pytest.mark.asyncio
    async def test_latency_rounded_to_one_decimal(self, monitor):
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"1.2.3.4\n", b""))
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            ok, latency = await monitor.check_dns("10.10.100.10")
        assert ok is True
        assert latency == round(latency, 1)

    @pytest.mark.asyncio
    async def test_multiple_ips_in_response_still_ok(self, monitor):
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"1.2.3.4\n5.6.7.8\n", b""))
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            ok, latency = await monitor.check_dns("10.10.100.10")
        assert ok is True
        assert latency is not None


class TestCheckDnsFailure:
    @pytest.mark.asyncio
    async def test_nonzero_returncode_returns_false_none(self, monitor):
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"connection refused"))
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            ok, latency = await monitor.check_dns("10.10.100.10")
        assert ok is False
        assert latency is None

    @pytest.mark.asyncio
    async def test_empty_stdout_returns_false_none(self, monitor):
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            ok, latency = await monitor.check_dns("10.10.100.10")
        assert ok is False
        assert latency is None

    @pytest.mark.asyncio
    async def test_whitespace_only_stdout_returns_false_none(self, monitor):
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"   \n", b""))
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            ok, latency = await monitor.check_dns("10.10.100.10")
        assert ok is False
        assert latency is None

    @pytest.mark.asyncio
    async def test_timeout_returns_false_none(self, monitor):
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
                ok, latency = await monitor.check_dns("10.10.100.10")
        assert ok is False
        assert latency is None

    @pytest.mark.asyncio
    async def test_os_error_returns_false_none(self, monitor):
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("no such file")):
            ok, latency = await monitor.check_dns("10.10.100.10")
        assert ok is False
        assert latency is None

    @pytest.mark.asyncio
    async def test_general_exception_returns_false_none(self, monitor):
        with patch("asyncio.create_subprocess_exec", side_effect=RuntimeError("unexpected")):
            ok, latency = await monitor.check_dns("10.10.100.10")
        assert ok is False
        assert latency is None

