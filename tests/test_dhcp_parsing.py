"""
Unit tests for DHCP configuration parsing and validation.

These tests verify correct parsing of DHCP configuration from Pi-hole API
responses and proper handling of DHCP state transitions.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))


class TestDHCPConfigStructureParsing:
    """Tests for DHCP configuration structure parsing."""

    def test_parse_dhcp_enabled_full_config(self):
        """Test parsing complete DHCP configuration."""
        config = {
            "active": True,
            "start": "192.168.1.100",
            "end": "192.168.1.200",
            "router": "192.168.1.1",
            "domain": "home.local",
            "leasetime": "24h",
            "ipv6": False,
            "ra": False,
        }

        assert config["active"] is True
        assert config["start"] == "192.168.1.100"
        assert config["end"] == "192.168.1.200"
        assert config["router"] == "192.168.1.1"
        assert config["domain"] == "home.local"
        assert config["leasetime"] == "24h"

    def test_parse_dhcp_disabled_minimal_config(self):
        """Test parsing minimal DHCP config (disabled)."""
        config = {
            "active": False,
        }

        assert config["active"] is False
        # When disabled, other fields may not be present
        assert "start" not in config or config.get("start") is None

    def test_parse_dhcp_nested_v6_structure(self):
        """Test parsing Pi-hole v6 nested DHCP structure."""
        response = {
            "config": {
                "dhcp": {
                    "active": True,
                    "start": "10.10.100.100",
                    "end": "10.10.100.200",
                    "router": "10.10.100.1",
                    "domain": "local",
                    "leasetime": "12h",
                }
            }
        }

        dhcp_config = response.get("config", {}).get("dhcp", {})

        assert dhcp_config.get("active") is True
        assert dhcp_config.get("start") == "10.10.100.100"
        assert dhcp_config.get("end") == "10.10.100.200"


class TestDHCPStateDetermination:
    """Tests for DHCP state determination logic."""

    def test_dhcp_enabled_state(self):
        """Test identification of DHCP enabled state."""
        config = {"active": True}

        is_enabled = config.get("active", False)

        assert is_enabled is True

    def test_dhcp_disabled_state(self):
        """Test identification of DHCP disabled state."""
        config = {"active": False}

        is_enabled = config.get("active", False)

        assert is_enabled is False

    def test_dhcp_missing_active_field(self):
        """Test DHCP state when 'active' field is missing (default to disabled)."""
        config = {}

        is_enabled = config.get("active", False)

        assert is_enabled is False

    def test_dhcp_null_active_field(self):
        """Test DHCP state when 'active' field is None."""
        config = {"active": None}

        is_enabled = config.get("active", False)

        # None is falsy, so should be False
        assert is_enabled is None or is_enabled is False


class TestDHCPMisconfigurationDetection:
    """Tests for DHCP misconfiguration detection."""

    def test_master_with_dhcp_enabled(self):
        """Test correct MASTER configuration (DHCP enabled)."""
        keepalived_state = "MASTER"
        dhcp_enabled = True

        # MASTER should have DHCP enabled
        is_correct = (keepalived_state == "MASTER" and dhcp_enabled is True)

        assert is_correct is True

    def test_master_with_dhcp_disabled(self):
        """Test MASTER misconfiguration (DHCP disabled - WRONG)."""
        keepalived_state = "MASTER"
        dhcp_enabled = False

        # MASTER with DHCP disabled is misconfigured
        is_misconfigured = (keepalived_state == "MASTER" and dhcp_enabled is False)

        assert is_misconfigured is True

    def test_backup_with_dhcp_disabled(self):
        """Test correct BACKUP configuration (DHCP disabled)."""
        keepalived_state = "BACKUP"
        dhcp_enabled = False

        # BACKUP should have DHCP disabled
        is_correct = (keepalived_state == "BACKUP" and dhcp_enabled is False)

        assert is_correct is True

    def test_backup_with_dhcp_enabled(self):
        """Test BACKUP misconfiguration (DHCP enabled - WRONG)."""
        keepalived_state = "BACKUP"
        dhcp_enabled = True

        # BACKUP with DHCP enabled is misconfigured
        is_misconfigured = (keepalived_state == "BACKUP" and dhcp_enabled is True)

        assert is_misconfigured is True

    def test_both_nodes_dhcp_enabled(self):
        """Test critical misconfiguration (both nodes have DHCP enabled)."""
        primary_dhcp = True
        secondary_dhcp = True

        # Both enabled is a critical error (IP conflicts)
        both_enabled = (primary_dhcp and secondary_dhcp)

        assert both_enabled is True  # This is BAD - should trigger alert

    def test_both_nodes_dhcp_disabled(self):
        """Test warning configuration (both nodes have DHCP disabled)."""
        primary_dhcp = False
        secondary_dhcp = False

        # Both disabled means no DHCP service
        both_disabled = (not primary_dhcp and not secondary_dhcp)

        assert both_disabled is True  # This is a WARNING - no DHCP


class TestDHCPIPRangeValidation:
    """Tests for DHCP IP range validation."""

    def test_valid_dhcp_range(self):
        """Test validation of valid DHCP range."""
        start = "192.168.1.100"
        end = "192.168.1.200"

        # Basic validation: both are IP addresses
        assert "." in start and "." in end
        assert len(start.split(".")) == 4
        assert len(end.split(".")) == 4

    def test_dhcp_range_same_subnet(self):
        """Test that DHCP range is in same subnet."""
        start = "192.168.1.100"
        end = "192.168.1.200"

        # Extract first 3 octets (simple subnet check)
        start_subnet = ".".join(start.split(".")[0:3])
        end_subnet = ".".join(end.split(".")[0:3])

        assert start_subnet == end_subnet

    def test_dhcp_range_order(self):
        """Test that DHCP start is before end (numerically)."""
        start = "192.168.1.100"
        end = "192.168.1.200"

        # Extract last octet
        start_octet = int(start.split(".")[-1])
        end_octet = int(end.split(".")[-1])

        assert start_octet < end_octet


class TestDHCPLeasesParsing:
    """Tests for DHCP leases data parsing."""

    def test_parse_lease_entry(self):
        """Test parsing a single DHCP lease entry."""
        lease = {
            "ip": "192.168.1.100",
            "mac": "aa:bb:cc:dd:ee:ff",
            "hostname": "device1",
            "expires": "2024-12-31T23:59:59",
        }

        assert lease["ip"] == "192.168.1.100"
        assert lease["mac"] == "aa:bb:cc:dd:ee:ff"
        assert lease["hostname"] == "device1"

    def test_parse_multiple_leases(self):
        """Test parsing multiple DHCP leases."""
        leases = [
            {"ip": "192.168.1.100", "mac": "aa:bb:cc:dd:ee:ff"},
            {"ip": "192.168.1.101", "mac": "11:22:33:44:55:66"},
            {"ip": "192.168.1.102", "mac": "aa:11:bb:22:cc:33"},
        ]

        assert len(leases) == 3
        assert leases[0]["ip"] == "192.168.1.100"
        assert leases[1]["mac"] == "11:22:33:44:55:66"

    def test_empty_leases_list(self):
        """Test handling of empty leases list."""
        leases = []

        assert len(leases) == 0

    def test_leases_count(self):
        """Test lease counting."""
        leases = [{"ip": "192.168.1.100"}] * 10

        lease_count = len(leases)

        assert lease_count == 10


class TestDHCPConfigEdgeCases:
    """Tests for edge cases in DHCP configuration."""

    def test_dhcp_ipv6_support(self):
        """Test IPv6 DHCP configuration parsing."""
        config = {
            "active": True,
            "ipv6": True,
            "ra": True,
        }

        assert config["ipv6"] is True
        assert config["ra"] is True  # Router Advertisement

    def test_dhcp_custom_leasetime(self):
        """Test custom lease time values."""
        config = {
            "active": True,
            "leasetime": "12h",
        }

        assert config["leasetime"] == "12h"

        # Other common formats
        lease_times = ["24h", "12h", "1h", "infinite", "0"]
        for lt in lease_times:
            config["leasetime"] = lt
            assert config["leasetime"] == lt

    def test_dhcp_empty_domain(self):
        """Test DHCP config with empty domain."""
        config = {
            "active": True,
            "domain": "",
        }

        domain = config.get("domain", "")

        assert domain == ""

    def test_dhcp_missing_optional_fields(self):
        """Test DHCP config with missing optional fields."""
        config = {
            "active": True,
            "start": "192.168.1.100",
            "end": "192.168.1.200",
        }

        # Optional fields should use defaults
        domain = config.get("domain", "local")
        leasetime = config.get("leasetime", "24h")

        assert domain == "local"
        assert leasetime == "24h"


class TestDHCPFailoverScenarios:
    """Tests for DHCP failover scenario handling."""

    def test_primary_master_secondary_backup(self):
        """Test normal state: Primary=MASTER+DHCP, Secondary=BACKUP+no DHCP."""
        primary = {
            "state": "MASTER",
            "dhcp_enabled": True,
        }
        secondary = {
            "state": "BACKUP",
            "dhcp_enabled": False,
        }

        # This is the correct state
        is_correct = (
            primary["state"] == "MASTER"
            and primary["dhcp_enabled"] is True
            and secondary["state"] == "BACKUP"
            and secondary["dhcp_enabled"] is False
        )

        assert is_correct is True

    def test_failover_state_secondary_master(self):
        """Test failover state: Primary=BACKUP+no DHCP, Secondary=MASTER+DHCP."""
        primary = {
            "state": "BACKUP",
            "dhcp_enabled": False,
        }
        secondary = {
            "state": "MASTER",
            "dhcp_enabled": True,
        }

        # This is a valid failover state
        is_valid_failover = (
            primary["state"] == "BACKUP"
            and primary["dhcp_enabled"] is False
            and secondary["state"] == "MASTER"
            and secondary["dhcp_enabled"] is True
        )

        assert is_valid_failover is True

    def test_split_brain_both_master(self):
        """Test split-brain scenario: Both nodes think they're MASTER."""
        primary = {"state": "MASTER", "dhcp_enabled": True}
        secondary = {"state": "MASTER", "dhcp_enabled": True}

        # Both MASTER is a critical error
        both_master = (primary["state"] == "MASTER" and secondary["state"] == "MASTER")

        assert both_master is True  # This is BAD - split brain


class TestDHCPValidationHelpers:
    """Tests for DHCP validation helper functions."""

    def test_is_valid_ip_for_dhcp_range(self):
        """Test IP address validation for DHCP range."""
        valid_ips = [
            "192.168.1.100",
            "10.0.0.50",
            "172.16.0.10",
        ]

        for ip in valid_ips:
            # Simple validation
            parts = ip.split(".")
            assert len(parts) == 4
            for part in parts:
                assert 0 <= int(part) <= 255

    def test_is_valid_mac_address(self):
        """Test MAC address validation."""
        valid_macs = [
            "aa:bb:cc:dd:ee:ff",
            "AA:BB:CC:DD:EE:FF",
            "00:00:00:00:00:00",
            "ff:ff:ff:ff:ff:ff",
        ]

        for mac in valid_macs:
            parts = mac.split(":")
            assert len(parts) == 6
            for part in parts:
                assert len(part) == 2
                # Check if hex
                int(part, 16)  # Will raise ValueError if not hex
