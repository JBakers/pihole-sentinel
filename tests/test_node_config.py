"""
Tests for M1-P1: Multi-node configuration loading (dashboard/monitor.py)
"""

import os
import pytest
import sys
from pathlib import Path

# Add dashboard to path so we can import monitor
dashboard_path = Path(__file__).parent.parent / "dashboard"
sys.path.insert(0, str(dashboard_path))

# Import after path is set
from monitor import load_node_config_from_env


@pytest.fixture
def clear_env():
    """Clear Pi-hole and legacy env vars before/after each test."""
    # Save original values
    original_env = {}
    keys_to_clear = []
    
    for key in list(os.environ.keys()):
        if key.startswith("PIHOLE_") or key.startswith("PRIMARY_") or key.startswith("SECONDARY_"):
            original_env[key] = os.environ[key]
            keys_to_clear.append(key)
    
    # Clear before test
    for key in keys_to_clear:
        del os.environ[key]
    
    yield
    
    # Clear after test
    for key in list(os.environ.keys()):
        if key.startswith("PIHOLE_") or key.startswith("PRIMARY_") or key.startswith("SECONDARY_"):
            if key in os.environ:
                del os.environ[key]
    
    # Restore original values
    for key, value in original_env.items():
        os.environ[key] = value


class TestNodeConfigNewFormat:
    """Tests for new PIHOLE_N_IP format"""
    
    def test_load_two_nodes_new_format(self, clear_env):
        """Load 2 nodes using new PIHOLE_N format."""
        os.environ["PIHOLE_1_IP"] = "10.0.0.1"
        os.environ["PIHOLE_1_PASSWORD"] = "pass1"
        os.environ["PIHOLE_2_IP"] = "10.0.0.2"
        os.environ["PIHOLE_2_PASSWORD"] = "pass2"
        
        nodes = load_node_config_from_env()
        
        assert len(nodes) == 2
        assert nodes[0]["index"] == 1
        assert nodes[0]["ip"] == "10.0.0.1"
        assert nodes[0]["password"] == "pass1"
        assert nodes[0]["name"] == "Node-1"  # default name
        assert nodes[0]["ssh_user"] == "root"  # default
        assert nodes[0]["ssh_port"] == 22  # default
        
        assert nodes[1]["index"] == 2
        assert nodes[1]["ip"] == "10.0.0.2"
        assert nodes[1]["password"] == "pass2"
    
    def test_load_three_nodes(self, clear_env):
        """Load 3 nodes."""
        os.environ["PIHOLE_1_IP"] = "10.0.0.1"
        os.environ["PIHOLE_1_PASSWORD"] = "pass1"
        os.environ["PIHOLE_2_IP"] = "10.0.0.2"
        os.environ["PIHOLE_2_PASSWORD"] = "pass2"
        os.environ["PIHOLE_3_IP"] = "10.0.0.3"
        os.environ["PIHOLE_3_PASSWORD"] = "pass3"
        os.environ["PIHOLE_3_NAME"] = "Tertiary"
        
        nodes = load_node_config_from_env()
        
        assert len(nodes) == 3
        assert nodes[2]["index"] == 3
        assert nodes[2]["ip"] == "10.0.0.3"
        assert nodes[2]["name"] == "Tertiary"  # custom name
    
    def test_load_five_nodes(self, clear_env):
        """Load 5 nodes."""
        for i in range(1, 6):
            os.environ[f"PIHOLE_{i}_IP"] = f"10.0.0.{i}"
            os.environ[f"PIHOLE_{i}_PASSWORD"] = f"pass{i}"
        
        nodes = load_node_config_from_env()
        
        assert len(nodes) == 5
        for i in range(5):
            assert nodes[i]["index"] == i + 1
            assert nodes[i]["ip"] == f"10.0.0.{i + 1}"
    
    def test_custom_node_names(self, clear_env):
        """Custom names for nodes."""
        os.environ["PIHOLE_1_IP"] = "10.0.0.1"
        os.environ["PIHOLE_1_PASSWORD"] = "pass1"
        os.environ["PIHOLE_1_NAME"] = "LXC-Primary"
        
        os.environ["PIHOLE_2_IP"] = "10.0.0.2"
        os.environ["PIHOLE_2_PASSWORD"] = "pass2"
        os.environ["PIHOLE_2_NAME"] = "RPi-Secondary"
        
        nodes = load_node_config_from_env()
        
        assert nodes[0]["name"] == "LXC-Primary"
        assert nodes[1]["name"] == "RPi-Secondary"
    
    def test_custom_ssh_settings_per_node(self, clear_env):
        """Custom SSH user/port per node."""
        os.environ["PIHOLE_1_IP"] = "10.0.0.1"
        os.environ["PIHOLE_1_PASSWORD"] = "pass1"
        os.environ["PIHOLE_1_SSH_USER"] = "admin"
        os.environ["PIHOLE_1_SSH_PORT"] = "2222"
        
        os.environ["PIHOLE_2_IP"] = "10.0.0.2"
        os.environ["PIHOLE_2_PASSWORD"] = "pass2"
        # Node 2 uses defaults
        
        nodes = load_node_config_from_env()
        
        assert nodes[0]["ssh_user"] == "admin"
        assert nodes[0]["ssh_port"] == 2222
        assert nodes[1]["ssh_user"] == "root"  # default
        assert nodes[1]["ssh_port"] == 22  # default
    
    def test_ssh_port_as_integer(self, clear_env):
        """SSH port is converted to int, not string."""
        os.environ["PIHOLE_1_IP"] = "10.0.0.1"
        os.environ["PIHOLE_1_PASSWORD"] = "pass1"
        os.environ["PIHOLE_1_SSH_PORT"] = "1234"
        os.environ["PIHOLE_2_IP"] = "10.0.0.2"
        os.environ["PIHOLE_2_PASSWORD"] = "pass2"
        
        nodes = load_node_config_from_env()
        
        assert isinstance(nodes[0]["ssh_port"], int)
        assert nodes[0]["ssh_port"] == 1234


class TestNodeConfigErrors:
    """Tests for error cases"""
    
    def test_missing_password_raises_error(self, clear_env):
        """Missing password for any node raises ValueError."""
        os.environ["PIHOLE_1_IP"] = "10.0.0.1"
        os.environ["PIHOLE_1_PASSWORD"] = "pass1"
        os.environ["PIHOLE_2_IP"] = "10.0.0.2"
        # Missing PIHOLE_2_PASSWORD
        
        with pytest.raises(ValueError, match="PIHOLE_2_PASSWORD"):
            load_node_config_from_env()
    
    def test_no_nodes_configured_raises_error(self, clear_env):
        """No nodes configured raises ValueError."""
        # Don't set any env vars
        
        with pytest.raises(ValueError, match="No Pi-hole nodes configured"):
            load_node_config_from_env()
    
    def test_single_node_raises_error(self, clear_env):
        """Only 1 node configured raises ValueError (minimum 2 required)."""
        os.environ["PIHOLE_1_IP"] = "10.0.0.1"
        os.environ["PIHOLE_1_PASSWORD"] = "pass1"
        
        with pytest.raises(ValueError, match="Minimum 2 nodes required"):
            load_node_config_from_env()
    
    def test_gap_in_node_numbers_detected(self, clear_env):
        """Gap in node numbers (e.g., 1, 3 missing 2) is detected and raises error."""
        os.environ["PIHOLE_1_IP"] = "10.0.0.1"
        os.environ["PIHOLE_1_PASSWORD"] = "pass1"
        os.environ["PIHOLE_3_IP"] = "10.0.0.3"  # Gap: missing PIHOLE_2_IP
        os.environ["PIHOLE_3_PASSWORD"] = "pass3"
        
        # Should raise error because we only load 1 node (stops at gap),
        # and minimum required is 2 nodes
        with pytest.raises(ValueError, match="Minimum 2 nodes required"):
            load_node_config_from_env()


class TestNodeConfigBackwardCompat:
    """Tests for backward compatibility with legacy format"""
    
    def test_backward_compat_legacy_format(self, clear_env):
        """Old PRIMARY_IP/SECONDARY_IP format still works (with warning)."""
        os.environ["PRIMARY_IP"] = "10.0.0.1"
        os.environ["PRIMARY_PASSWORD"] = "pass1"
        os.environ["SECONDARY_IP"] = "10.0.0.2"
        os.environ["SECONDARY_PASSWORD"] = "pass2"
        
        nodes = load_node_config_from_env()
        
        assert len(nodes) == 2
        assert nodes[0]["ip"] == "10.0.0.1"
        assert nodes[0]["password"] == "pass1"
        assert nodes[0]["index"] == 1
        assert nodes[1]["ip"] == "10.0.0.2"
        assert nodes[1]["password"] == "pass2"
        assert nodes[1]["index"] == 2
    
    def test_legacy_with_custom_names(self, clear_env):
        """Legacy format with custom PRIMARY_NAME/SECONDARY_NAME."""
        os.environ["PRIMARY_IP"] = "10.0.0.1"
        os.environ["PRIMARY_PASSWORD"] = "pass1"
        os.environ["PRIMARY_NAME"] = "MainBox"
        os.environ["SECONDARY_IP"] = "10.0.0.2"
        os.environ["SECONDARY_PASSWORD"] = "pass2"
        os.environ["SECONDARY_NAME"] = "BackupBox"
        
        nodes = load_node_config_from_env()
        
        assert nodes[0]["name"] == "MainBox"
        assert nodes[1]["name"] == "BackupBox"
    
    def test_legacy_with_ssh_settings(self, clear_env):
        """Legacy format with SSH settings per node."""
        os.environ["PRIMARY_IP"] = "10.0.0.1"
        os.environ["PRIMARY_PASSWORD"] = "pass1"
        os.environ["PRIMARY_SSH_USER"] = "admin"
        os.environ["PRIMARY_SSH_PORT"] = "2222"
        
        os.environ["SECONDARY_IP"] = "10.0.0.2"
        os.environ["SECONDARY_PASSWORD"] = "pass2"
        os.environ["SECONDARY_SSH_USER"] = "user"
        os.environ["SECONDARY_SSH_PORT"] = "22"
        
        nodes = load_node_config_from_env()
        
        assert nodes[0]["ssh_user"] == "admin"
        assert nodes[0]["ssh_port"] == 2222
        assert nodes[1]["ssh_user"] == "user"
        assert nodes[1]["ssh_port"] == 22
    
    def test_new_format_takes_precedence_over_legacy(self, clear_env):
        """If both formats exist, new format (PIHOLE_N) takes precedence."""
        # Set new format
        os.environ["PIHOLE_1_IP"] = "10.0.0.11"
        os.environ["PIHOLE_1_PASSWORD"] = "new_pass1"
        os.environ["PIHOLE_2_IP"] = "10.0.0.12"
        os.environ["PIHOLE_2_PASSWORD"] = "new_pass2"
        
        # Also set legacy (should be ignored)
        os.environ["PRIMARY_IP"] = "10.0.0.1"
        os.environ["PRIMARY_PASSWORD"] = "old_pass1"
        os.environ["SECONDARY_IP"] = "10.0.0.2"
        os.environ["SECONDARY_PASSWORD"] = "old_pass2"
        
        nodes = load_node_config_from_env()
        
        # Should load new format
        assert len(nodes) == 2
        assert nodes[0]["ip"] == "10.0.0.11"
        assert nodes[0]["password"] == "new_pass1"


class TestNodeIndexing:
    """Tests for node index consistency"""
    
    def test_node_indices_are_sequential(self, clear_env):
        """Node indices should be 1, 2, 3, ..."""
        for i in range(1, 5):
            os.environ[f"PIHOLE_{i}_IP"] = f"10.0.0.{i}"
            os.environ[f"PIHOLE_{i}_PASSWORD"] = f"pass{i}"
        
        nodes = load_node_config_from_env()
        
        for i, node in enumerate(nodes, start=1):
            assert node["index"] == i
    
    def test_node_dict_has_all_required_keys(self, clear_env):
        """Each node dict must have all required keys."""
        os.environ["PIHOLE_1_IP"] = "10.0.0.1"
        os.environ["PIHOLE_1_PASSWORD"] = "pass1"
        os.environ["PIHOLE_2_IP"] = "10.0.0.2"
        os.environ["PIHOLE_2_PASSWORD"] = "pass2"
        
        nodes = load_node_config_from_env()
        
        required_keys = {"index", "ip", "name", "password", "ssh_user", "ssh_port"}
        for node in nodes:
            assert set(node.keys()) == required_keys
