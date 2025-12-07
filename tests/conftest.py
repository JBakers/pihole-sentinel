"""
Pytest configuration and shared fixtures for Pi-hole Sentinel tests.

This module provides common test fixtures and configuration for all test modules.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from aiohttp import ClientSession

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# Session-scoped fixtures (run once per test session)
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for the entire test session.

    This fixture ensures all async tests share the same event loop,
    improving test performance and avoiding event loop conflicts.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """
    Return path to test data directory.

    This directory contains fixture files, mock responses, and test configurations.
    """
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


# ============================================================================
# Function-scoped fixtures (run once per test function)
# ============================================================================

@pytest.fixture
def sample_config() -> dict:
    """
    Provide a sample configuration dictionary for testing.

    Returns valid configuration values that can be used in tests.
    Does NOT use real credentials or production values.
    """
    return {
        "primary_ip": "10.10.100.10",
        "primary_name": "Primary Pi-hole",
        "primary_password": "test_password_primary",
        "secondary_ip": "10.10.100.20",
        "secondary_name": "Secondary Pi-hole",
        "secondary_password": "test_password_secondary",
        "vip_address": "10.10.100.2",
        "check_interval": 10,
        "db_path": ":memory:",  # Use in-memory SQLite for tests
        "api_key": "test_api_key_123456789",
    }


@pytest.fixture
def sample_network_config() -> dict:
    """
    Provide sample network configuration for setup.py tests.
    """
    return {
        "interface": "eth0",
        "primary_ip": "192.168.1.10",
        "secondary_ip": "192.168.1.11",
        "vip_address": "192.168.1.2",
        "gateway_ip": "192.168.1.1",
        "enable_dhcp_failover": True,
    }


@pytest_asyncio.fixture
async def http_session() -> AsyncGenerator[ClientSession, None]:
    """
    Provide an aiohttp ClientSession for async HTTP tests.

    The session is automatically closed after the test completes.
    """
    session = ClientSession()
    yield session
    await session.close()


@pytest.fixture
def mock_env_vars(monkeypatch) -> None:
    """
    Set mock environment variables for testing.

    This prevents tests from accidentally using real credentials
    or production configuration.
    """
    test_env = {
        "PRIMARY_IP": "10.10.100.10",
        "PRIMARY_PASSWORD": "test_password",
        "SECONDARY_IP": "10.10.100.20",
        "SECONDARY_PASSWORD": "test_password",
        "VIP_ADDRESS": "10.10.100.2",
        "CHECK_INTERVAL": "10",
        "DB_PATH": ":memory:",
        "API_KEY": "test_api_key",
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)


# ============================================================================
# Mock data fixtures
# ============================================================================

@pytest.fixture
def mock_pihole_auth_response() -> dict:
    """
    Mock successful Pi-hole authentication response.
    """
    return {
        "session": {
            "sid": "test_session_id_123456",
            "validity": 3600,
            "valid": True,
            "totp": False,
        }
    }


@pytest.fixture
def mock_pihole_stats_response() -> dict:
    """
    Mock Pi-hole stats/summary API response.
    """
    return {
        "gravity": {
            "domains_being_blocked": 150000,
            "last_update": {
                "absolute": 1699564800,
                "relative": {"days": 0, "hours": 2, "minutes": 30},
            },
        },
        "queries": {
            "total": 12345,
            "blocked": 2345,
            "percent_blocked": 19.0,
        },
        "clients": {
            "total": 15,
            "active": 8,
        },
    }


@pytest.fixture
def mock_dhcp_config_enabled() -> dict:
    """
    Mock DHCP configuration with DHCP enabled.
    """
    return {
        "active": True,
        "start": "192.168.1.100",
        "end": "192.168.1.200",
        "router": "192.168.1.1",
        "domain": "home.local",
        "leasetime": "24h",
        "ipv6": False,
        "ra": False,
    }


@pytest.fixture
def mock_dhcp_config_disabled() -> dict:
    """
    Mock DHCP configuration with DHCP disabled.
    """
    return {
        "active": False,
    }


# ============================================================================
# Utility functions for tests
# ============================================================================

def assert_valid_ip(ip: str) -> None:
    """
    Assert that a string is a valid IPv4 address.

    Args:
        ip: IP address string to validate

    Raises:
        AssertionError: If IP is invalid
    """
    parts = ip.split(".")
    assert len(parts) == 4, f"IP {ip} does not have 4 octets"
    for part in parts:
        assert part.isdigit(), f"IP {ip} contains non-numeric octet: {part}"
        num = int(part)
        assert 0 <= num <= 255, f"IP {ip} has octet out of range: {num}"


def assert_valid_interface(interface: str) -> None:
    """
    Assert that a string is a valid network interface name.

    Args:
        interface: Interface name to validate

    Raises:
        AssertionError: If interface name is invalid
    """
    assert len(interface) > 0, "Interface name is empty"
    assert len(interface) <= 15, f"Interface name too long: {interface}"
    assert interface[0].isalpha(), f"Interface must start with letter: {interface}"
