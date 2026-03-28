"""Tests for notification classification on MASTER switches."""

import importlib
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def monitor_module(monkeypatch, tmp_path):
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
    return importlib.import_module("dashboard.monitor")


def test_collect_node_issues_reports_offline_host(monitor_module):
    issues = monitor_module.collect_node_issues(
        "Primary",
        {"online": False, "pihole": False},
        False,
    )

    assert issues == ["Primary host is offline"]


def test_collect_node_issues_reports_service_and_dns(monitor_module):
    issues = monitor_module.collect_node_issues(
        "Secondary",
        {"online": True, "pihole": False},
        False,
    )

    assert issues == [
        "Pi-hole service on Secondary is down",
        "DNS resolution on Secondary is failing",
    ]


def test_switch_to_secondary_is_classified_as_failover(monitor_module):
    event_type, reason = monitor_module.describe_master_transition(
        previous_master="primary",
        current_master="secondary",
        primary_data={"online": True, "pihole": False},
        secondary_data={"online": True, "pihole": True},
        primary_dns=False,
        secondary_dns=True,
        previous_primary_online=True,
        previous_primary_pihole=True,
        previous_primary_dns=True,
    )

    assert event_type == "failover"
    assert reason == "Pi-hole service on Primary is down; DNS resolution on Primary is failing"


def test_primary_reclaiming_master_after_recovery_uses_recovery(monitor_module):
    event_type, reason = monitor_module.describe_master_transition(
        previous_master="secondary",
        current_master="primary",
        primary_data={"online": True, "pihole": True},
        secondary_data={"online": True, "pihole": True},
        primary_dns=True,
        secondary_dns=True,
        previous_primary_online=False,
        previous_primary_pihole=False,
        previous_primary_dns=False,
    )

    assert event_type == "recovery"
    assert "host back online" in reason.lower()
    assert "Pi-hole service restored" in reason
    assert "DNS restored" in reason


def test_primary_switch_due_to_secondary_problem_stays_failover(monitor_module):
    event_type, reason = monitor_module.describe_master_transition(
        previous_master="secondary",
        current_master="primary",
        primary_data={"online": True, "pihole": True},
        secondary_data={"online": False, "pihole": False},
        primary_dns=True,
        secondary_dns=False,
        previous_primary_online=True,
        previous_primary_pihole=True,
        previous_primary_dns=True,
    )

    assert event_type == "failover"
    assert reason == "Secondary host is offline"
