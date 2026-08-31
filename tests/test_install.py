"""
Tests for install.py — preflight checks, rollback, and uninstall logic.

Unit tests run without any external dependencies (SSH/Docker mocked).
Integration tests (marked 'docker') require the Docker test environment:
    make docker-up
    pytest -m docker tests/test_install.py

Docker endpoints used in integration tests:
    Primary mock Pi-hole:   http://localhost:8001  (password: testpass123)
    Secondary mock Pi-hole: http://localhost:8002  (password: testpass123)
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from install import SetupConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**overrides):
    """Return a minimal SetupConfig pre-loaded with a test config dict."""
    c = SetupConfig()
    c.config.update(
        {
            "separate_monitor": True,
            "monitor_ip": "10.99.0.20",
            "monitor_ssh_user": "root",
            "monitor_ssh_port": "22",
            "primary_ip": "10.99.0.10",
            "primary_ssh_user": "root",
            "primary_ssh_port": "22",
            "primary_password": "testpass123",
            "secondary_ip": "10.99.0.11",
            "secondary_ssh_user": "root",
            "secondary_ssh_port": "22",
            "secondary_password": "testpass123",
            "ssh_key_path": None,
            **overrides,
        }
    )
    return c


# ---------------------------------------------------------------------------
# _check_pihole_api  (unit)
# ---------------------------------------------------------------------------


class TestCheckPiholeApi:
    """Unit tests for SetupConfig._check_pihole_api()."""

    def test_valid_password_returns_ok(self):
        """Successful API auth → (True, 'OK')."""
        c = _make_config()
        good_response = b'{"session":{"valid":true,"sid":"abc123"}}'
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = good_response

        with patch("urllib.request.urlopen", return_value=mock_resp):
            ok, msg = c._check_pihole_api("10.0.0.1", "correctpass")

        assert ok is True
        assert msg == "OK"

    def test_wrong_password_returns_false(self):
        """API returns valid=false → (False, message)."""
        c = _make_config()
        bad_response = b'{"session":{"valid":false,"sid":null}}'
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = bad_response

        with patch("urllib.request.urlopen", return_value=mock_resp):
            ok, msg = c._check_pihole_api("10.0.0.1", "wrongpass")

        assert ok is False
        assert "wrong password" in msg

    def test_http_error_returns_false(self):
        """HTTP error (401/500) → (False, message with code)."""
        import urllib.error

        c = _make_config()

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(None, 401, "Unauthorized", {}, None),
        ):
            ok, msg = c._check_pihole_api("10.0.0.1", "bad")

        assert ok is False
        assert "401" in msg

    def test_unreachable_host_returns_false(self):
        """Connection refused / timeout → (False, message)."""
        import urllib.error

        c = _make_config()

        with patch(
            "urllib.request.urlopen", side_effect=urllib.error.URLError("refused")
        ):
            ok, msg = c._check_pihole_api("10.0.0.1", "pass")

        assert ok is False
        assert "unreachable" in msg

    def test_invalid_ip_returns_false_without_http_request(self):
        """An invalid host cannot be used to construct an API request."""
        c = _make_config()

        with patch("urllib.request.urlopen") as urlopen:
            ok, msg = c._check_pihole_api("example.com", "pass")

        assert ok is False
        assert msg == "invalid IP address"
        urlopen.assert_not_called()

    def test_invalid_localhost_port_returns_false_without_http_request(self):
        """A malformed local Docker endpoint cannot construct an API request."""
        c = _make_config()

        with patch("urllib.request.urlopen") as urlopen:
            ok, msg = c._check_pihole_api("localhost:not-a-port", "pass")

        assert ok is False
        assert msg == "invalid IP address"
        urlopen.assert_not_called()


# ---------------------------------------------------------------------------
# Remote staging cleanup (unit)
# ---------------------------------------------------------------------------


class TestRemoteStagingCleanup:
    """Unit tests for SetupConfig.cleanup_remote_staging_dir()."""

    def test_cleanup_removes_staging_dir(self):
        """Successful cleanup issues a guarded removal command."""
        c = _make_config()

        with patch.object(c, "remote_exec") as remote_exec:
            c.cleanup_remote_staging_dir(
                "10.0.0.1", "root", "22", "~/.cache/staging", "password"
            )

        remote_exec.assert_called_once_with(
            "10.0.0.1", "root", "22", "rm -rf -- ~/.cache/staging", "password"
        )

    def test_cleanup_suppresses_remote_failure(self):
        """A cleanup failure cannot mask a preceding deployment result."""
        c = _make_config()

        with patch.object(
            c,
            "remote_exec",
            side_effect=subprocess.CalledProcessError(255, "ssh"),
        ):
            c.cleanup_remote_staging_dir(
                "10.0.0.1", "root", "22", "~/.cache/staging"
            )


# ---------------------------------------------------------------------------
# preflight_checks  (unit)
# ---------------------------------------------------------------------------


class TestPreflightChecks:
    """Unit tests for SetupConfig.preflight_checks()."""

    def test_all_ok_passes(self, capsys):
        """All SSH + API checks pass → no sys.exit."""
        c = _make_config()

        with patch.object(c, "remote_exec") as mock_ssh, patch.object(
            c, "_check_pihole_api", return_value=(True, "OK")
        ):
            c.preflight_checks()  # must not raise / exit

        # remote_exec called for monitor + primary + secondary (3 SSH checks)
        assert mock_ssh.call_count == 3

    def test_ssh_failure_exits(self, capsys):
        """SSH failure on one host → sys.exit(1)."""
        c = _make_config()

        def ssh_fails(host, user, port, cmd):
            if host == "10.99.0.10":
                raise subprocess.CalledProcessError(255, "ssh")

        with patch.object(c, "remote_exec", side_effect=ssh_fails), patch.object(
            c, "_check_pihole_api", return_value=(True, "OK")
        ):
            with pytest.raises(SystemExit) as exc:
                c.preflight_checks()

        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "SSH login failed" in out

    def test_api_failure_exits(self, capsys):
        """Wrong Pi-hole password → sys.exit(1)."""
        c = _make_config()

        with patch.object(c, "remote_exec"), patch.object(
            c, "_check_pihole_api", return_value=(False, "wrong password")
        ):
            with pytest.raises(SystemExit) as exc:
                c.preflight_checks()

        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "wrong password" in out

    def test_multiple_failures_shown_all(self, capsys):
        """Multiple failures are all reported before exiting."""
        c = _make_config()

        with patch.object(
            c, "remote_exec", side_effect=subprocess.CalledProcessError(255, "ssh")
        ), patch.object(c, "_check_pihole_api", return_value=(False, "wrong password")):
            with pytest.raises(SystemExit):
                c.preflight_checks()

        out = capsys.readouterr().out
        # SSH failures for all 3 hosts + 2 API check failures
        assert out.count("✗") >= 3

    def test_no_separate_monitor_skips_monitor_ssh(self):
        """Without separate monitor, no SSH check for monitor."""
        c = _make_config(separate_monitor=False)

        with patch.object(c, "remote_exec") as mock_ssh, patch.object(
            c, "_check_pihole_api", return_value=(True, "OK")
        ):
            c.preflight_checks()

        # Only primary + secondary SSH = 2 calls
        assert mock_ssh.call_count == 2


# ---------------------------------------------------------------------------
# rollback_deployment  (unit)
# ---------------------------------------------------------------------------


class TestRollbackDeployment:
    """Unit tests for SetupConfig.rollback_deployment()."""

    def _make_deployed_hosts(self):
        return [
            {
                "type": "monitor",
                "host": "10.99.0.20",
                "user": "root",
                "port": "22",
                "backup_ts": "20260328_120000",
            },
            {
                "type": "primary",
                "host": "10.99.0.10",
                "user": "root",
                "port": "22",
                "backup_ts": "20260328_120001",
            },
            {
                "type": "secondary",
                "host": "10.99.0.11",
                "user": "root",
                "port": "22",
                "backup_ts": "20260328_120002",
            },
        ]

    def test_rollback_calls_remote_exec_for_each_host(self):
        """remote_exec must be called for all deployed hosts."""
        c = _make_config()
        hosts = self._make_deployed_hosts()

        with patch.object(c, "remote_exec") as mock_exec:
            c.rollback_deployment(hosts)

        # At least one call per host (file restore + service restart)
        called_hosts = {call_args.args[0] for call_args in mock_exec.call_args_list}
        assert "10.99.0.20" in called_hosts
        assert "10.99.0.10" in called_hosts
        assert "10.99.0.11" in called_hosts

    def test_rollback_restores_in_reverse_order(self):
        """Secondary is rolled back before primary (reverse deploy order)."""
        c = _make_config()
        hosts = self._make_deployed_hosts()
        call_order = []

        def track(host, user, port, cmd):
            call_order.append(host)

        with patch.object(c, "remote_exec", side_effect=track):
            c.rollback_deployment(hosts)

        # First host touched in rollback should be 10.99.0.11 (secondary)
        assert call_order[0] == "10.99.0.11"

    def test_rollback_empty_list_is_noop(self, capsys):
        """Empty deployed_hosts → nothing called, no crash."""
        c = _make_config()
        with patch.object(c, "remote_exec") as mock_exec:
            c.rollback_deployment([])
        mock_exec.assert_not_called()

    def test_rollback_tolerates_remote_exec_failure(self):
        """If remote_exec raises during rollback, it should not propagate."""
        c = _make_config()
        hosts = self._make_deployed_hosts()

        with patch.object(c, "remote_exec", side_effect=Exception("SSH down")):
            # Must not raise
            c.rollback_deployment(hosts)

    def test_rollback_without_backup_ts_skips_file_restore(self, capsys):
        """Host without backup_ts gets a restart attempt but no cp commands."""
        c = _make_config()
        hosts = [
            {
                "type": "primary",
                "host": "10.99.0.10",
                "user": "root",
                "port": "22",
                "backup_ts": None,
            }
        ]
        cp_calls = []

        def track(host, user, port, cmd):
            if cmd.startswith("[ -f"):
                cp_calls.append(cmd)

        with patch.object(c, "remote_exec", side_effect=track):
            c.rollback_deployment(hosts)

        assert len(cp_calls) == 0
        out = capsys.readouterr().out
        assert "No backup timestamp" in out


# ---------------------------------------------------------------------------
# uninstall  (unit)
# ---------------------------------------------------------------------------


class TestUninstall:
    """Unit tests for SetupConfig.uninstall()."""

    def test_uninstall_stops_services(self, monkeypatch):
        """Confirm stop/disable commands are issued for monitor and both nodes."""
        c = _make_config()
        exec_calls = []

        with patch.object(
            c,
            "remote_exec",
            side_effect=lambda h, u, p, cmd: exec_calls.append((h, cmd)),
        ), patch("builtins.input", return_value="yes"):
            c.uninstall()

        all_cmds = " ".join(cmd for _, cmd in exec_calls)
        assert "systemctl stop  pihole-monitor" in all_cmds
        assert "systemctl disable pihole-monitor" in all_cmds
        assert "systemctl stop  keepalived" in all_cmds
        assert "systemctl disable keepalived" in all_cmds

    def test_uninstall_removes_files(self, monkeypatch):
        """Sentinel-managed files must be deleted."""
        c = _make_config()
        exec_calls = []

        with patch.object(
            c, "remote_exec", side_effect=lambda h, u, p, cmd: exec_calls.append(cmd)
        ), patch("builtins.input", return_value="yes"):
            c.uninstall()

        all_cmds = " ".join(exec_calls)
        assert "/opt/pihole-monitor" in all_cmds
        assert "/etc/keepalived/keepalived.conf" in all_cmds
        assert "/usr/local/bin/check_pihole_service.sh" in all_cmds
        assert "/usr/local/bin/keepalived_notify.sh" in all_cmds

    def test_uninstall_cancelled_by_user(self, capsys):
        """Input other than 'yes' cancels without touching any server."""
        c = _make_config()

        with patch.object(c, "remote_exec") as mock_exec, patch(
            "builtins.input", return_value="no"
        ):
            c.uninstall()

        mock_exec.assert_not_called()
        out = capsys.readouterr().out
        assert "cancelled" in out.lower()

    def test_uninstall_no_separate_monitor_skips_monitor_host(self):
        """Without separate monitor, pihole-monitor removal targets primary."""
        c = _make_config(separate_monitor=False, monitor_ip=None)
        exec_calls = []

        with patch.object(
            c,
            "remote_exec",
            side_effect=lambda h, u, p, cmd: exec_calls.append((h, cmd)),
        ), patch("builtins.input", return_value="yes"):
            c.uninstall()

        # No calls against 10.99.0.20 (monitor-only IP)
        monitor_calls = [h for h, _ in exec_calls if h == "10.99.0.20"]
        assert len(monitor_calls) == 0

    def test_uninstall_tolerates_remote_exec_failure(self):
        """SSH errors during uninstall are reported but don't crash setup."""
        c = _make_config()

        with patch.object(
            c, "remote_exec", side_effect=Exception("connection refused")
        ), patch("builtins.input", return_value="yes"):
            # Must not raise
            c.uninstall()


# ---------------------------------------------------------------------------
# backup_existing_configs  — return value (unit)
# ---------------------------------------------------------------------------


class TestBackupExistingConfigs:
    """Verify backup_existing_configs() returns the timestamp string."""

    def _run_backup(self, c, stdout_value):
        """Helper: patch remote_exec to return stdout_value, run backup."""
        mock_result = MagicMock()
        mock_result.stdout = stdout_value

        with patch("subprocess.run", return_value=mock_result):
            return c.backup_existing_configs(
                "10.99.0.20", "root", "22", config_type="monitor"
            )

    def test_returns_timestamp_when_files_backed_up(self):
        c = _make_config()
        ts = self._run_backup(c, "backed_up")
        # Should be a timestamp string like '20260328_120000'
        assert ts is not None
        assert len(ts) == 15  # YYYYmmdd_HHMMSS
        assert "_" in ts

    def test_returns_none_when_nothing_backed_up(self):
        c = _make_config()
        ts = self._run_backup(c, "not_found")
        assert ts is None


# ---------------------------------------------------------------------------
# N-node support (M1-P4)  (unit)
# ---------------------------------------------------------------------------


def _make_nnode_config(num_nodes=3):
    """Return a SetupConfig populated with an N-node config dict."""
    c = SetupConfig()
    nodes = []
    for i in range(1, num_nodes + 1):
        nodes.append(
            {
                "index": i,
                "ip": f"10.99.0.{10 + i}",
                "name": c._node_name(i, num_nodes),
                "password": f"pass{i}",
                "ssh_user": "root",
                "ssh_port": "22",
                "priority": 150 - (i - 1) * 10,
                "state": "MASTER" if i == 1 else "BACKUP",
            }
        )
    c.config.update(
        {
            "interface": "eth0",
            "nodes": nodes,
            "primary_ip": nodes[0]["ip"],
            "secondary_ip": nodes[1]["ip"],
            "primary_password": nodes[0]["password"],
            "secondary_password": nodes[1]["password"],
            "primary_ssh_user": "root",
            "primary_ssh_port": "22",
            "secondary_ssh_user": "root",
            "secondary_ssh_port": "22",
            "vip": "10.99.0.100",
            "gateway": "10.99.0.1",
            "netmask": "24",
            "keepalived_password": "abc12345",
            "separate_monitor": True,
            "monitor_ip": "10.99.0.20",
            "monitor_ssh_user": "root",
            "monitor_ssh_port": "22",
            "dhcp_enabled": False,
        }
    )
    return c


class TestNodeHelpers:
    """Unit tests for the N-node helper methods."""

    def test_node_name_primary_secondary_then_numbered(self):
        c = SetupConfig()
        assert c._node_name(1, 3) == "Pi-Hole Node 1"
        assert c._node_name(2, 3) == "Pi-Hole Node 2"
        assert c._node_name(3, 3) == "Pi-Hole Node 3"

    def test_config_nodes_returns_explicit_list(self):
        c = _make_nnode_config(4)
        nodes = c._config_nodes()
        assert len(nodes) == 4
        assert [n["index"] for n in nodes] == [1, 2, 3, 4]

    def test_config_nodes_legacy_fallback(self):
        """Without 'nodes', a 2-node list is synthesised from legacy keys."""
        c = _make_config()  # legacy-only config, no 'nodes'
        nodes = c._config_nodes()
        assert len(nodes) == 2
        assert nodes[0]["ip"] == "10.99.0.10"
        assert nodes[0]["state"] == "MASTER"
        assert nodes[1]["state"] == "BACKUP"

    def test_priorities_descend_by_ten(self):
        c = _make_nnode_config(4)
        priorities = [n["priority"] for n in c.config["nodes"]]
        assert priorities == [150, 140, 130, 120]


class TestGenerateConfigsNNode:
    """Unit tests for N-node config generation."""

    def test_keepalived_conf_per_node(self):
        c = _make_nnode_config(3)
        node3 = c.config["nodes"][2]
        conf = c._build_keepalived_conf(node3)
        assert "router_id PIHOLE3" in conf
        assert "state BACKUP" in conf
        assert "priority 130" in conf
        assert "10.99.0.100/24" in conf

    def test_keepalived_conf_master_first_node(self):
        c = _make_nnode_config(3)
        conf = c._build_keepalived_conf(c.config["nodes"][0])
        assert "state MASTER" in conf
        assert "priority 150" in conf
        assert "router_id PIHOLE1" in conf

    def test_generate_configs_writes_all_node_files(self, tmp_path, monkeypatch):
        c = _make_nnode_config(3)
        monkeypatch.chdir(tmp_path)
        c.generate_configs()

        gen = tmp_path / "generated_configs"
        # Per-node files for all 3 nodes
        for i in (1, 2, 3):
            assert (gen / f"node{i}_keepalived.conf").exists()
            assert (gen / f"node{i}.env").exists()
        # Legacy aliases for node 1 & 2
        assert (gen / "primary_keepalived.conf").exists()
        assert (gen / "secondary_keepalived.conf").exists()
        assert (gen / "monitor.env").exists()

    def test_monitor_env_has_pihole_n_and_legacy(self, tmp_path, monkeypatch):
        c = _make_nnode_config(3)
        monkeypatch.chdir(tmp_path)
        c.generate_configs()

        env = (tmp_path / "generated_configs" / "monitor.env").read_text()
        # New N-node format
        assert "PIHOLE_1_IP=10.99.0.11" in env
        assert "PIHOLE_2_IP=10.99.0.12" in env
        assert "PIHOLE_3_IP=10.99.0.13" in env
        assert "PIHOLE_3_PASSWORD=pass3" in env
        # Legacy aliases
        assert "PRIMARY_IP=10.99.0.11" in env
        assert "SECONDARY_IP=10.99.0.12" in env

    def test_node_env_has_correct_priority_state(self, tmp_path, monkeypatch):
        c = _make_nnode_config(3)
        monkeypatch.chdir(tmp_path)
        c.generate_configs()

        env3 = (tmp_path / "generated_configs" / "node3.env").read_text()
        assert "NODE_PRIORITY=130" in env3
        assert "NODE_STATE=BACKUP" in env3


class TestPreflightNNode:
    """preflight_checks() must check every configured node."""

    def test_preflight_checks_all_nodes(self):
        c = _make_nnode_config(3)

        with patch.object(c, "remote_exec") as mock_ssh, patch.object(
            c, "_check_pihole_api", return_value=(True, "OK")
        ) as mock_api:
            c.preflight_checks()

        # monitor + 3 nodes = 4 SSH checks; 3 API checks
        assert mock_ssh.call_count == 4
        assert mock_api.call_count == 3


# ---------------------------------------------------------------------------
# Integration tests — require running Docker environment
# ---------------------------------------------------------------------------

DOCKER_PRIMARY_URL = "http://localhost:8001"
DOCKER_SECONDARY_URL = "http://localhost:8002"
DOCKER_PASSWORD = "testpass123"
DOCKER_WRONG_PW = "definitely-wrong"


def _docker_available():
    """Return True if the Docker mock Pi-holes are reachable."""
    import urllib.error
    import urllib.request

    try:
        urllib.request.urlopen(f"{DOCKER_PRIMARY_URL}/mock/state", timeout=2)
        return True
    except Exception:
        return False


docker = pytest.mark.skipif(
    not _docker_available(),
    reason=(
        "Docker test environment not running "
        "(run 'make docker-up' or 'docker compose -f docker-compose.test.yml up -d')"
    ),
)


@docker
class TestCheckPiholeApiDocker:
    """Integration tests for _check_pihole_api against the live mock Pi-holes."""

    def test_primary_correct_password(self):
        c = _make_config()
        ok, msg = c._check_pihole_api("localhost:8001".split(":")[0], DOCKER_PASSWORD)
        # Direct call with host:port doesn't work — use the full URL approach.
        # The method builds http://{ip}/api/auth so we need to patch it to
        # use the correct port.  Re-test via monkeypatching the URL:
        import json as _json
        import urllib.request

        url = f"{DOCKER_PRIMARY_URL}/api/auth"
        payload = _json.dumps({"password": DOCKER_PASSWORD}).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = _json.loads(resp.read().decode())
        assert body["session"]["valid"] is True

    def test_primary_wrong_password(self):
        import json as _json
        import urllib.error
        import urllib.request

        url = f"{DOCKER_PRIMARY_URL}/api/auth"
        payload = _json.dumps({"password": DOCKER_WRONG_PW}).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # Mock Pi-hole returns 401 for wrong password
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req, timeout=8)
        assert exc_info.value.code == 401

    def test_secondary_correct_password(self):
        import json as _json
        import urllib.request

        url = f"{DOCKER_SECONDARY_URL}/api/auth"
        payload = _json.dumps({"password": DOCKER_PASSWORD}).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = _json.loads(resp.read().decode())
        assert body["session"]["valid"] is True

    def test_check_pihole_api_with_port_in_url(self):
        """`_check_pihole_api` uses http://{ip}/api/auth — override ip to include port."""
        # Since _check_pihole_api constructs 'http://{ip}/api/auth' we use
        # 'localhost:8001' as the IP to hit the Docker container.
        c = _make_config()
        ok, msg = c._check_pihole_api("localhost:8001", DOCKER_PASSWORD)
        assert ok is True, f"Expected ok=True, got: {msg}"

    def test_check_pihole_api_wrong_password_via_method(self):
        c = _make_config()
        ok, msg = c._check_pihole_api("localhost:8001", DOCKER_WRONG_PW)
        assert ok is False

    def test_preflight_api_checks_pass_with_docker(self, capsys):
        """preflight_checks() Pi-hole API part passes with Docker mock."""
        c = _make_config(
            primary_ip="localhost:8001",
            secondary_ip="localhost:8002",
        )
        # Mock SSH so only API is exercised
        with patch.object(c, "remote_exec"):
            c.preflight_checks()  # must not sys.exit

    def test_preflight_api_checks_fail_with_wrong_password(self, capsys):
        """preflight_checks() exits when passwords are wrong."""
        c = _make_config(
            primary_ip="localhost:8001",
            secondary_ip="localhost:8002",
            primary_password=DOCKER_WRONG_PW,
            secondary_password=DOCKER_WRONG_PW,
        )
        with patch.object(c, "remote_exec"), pytest.raises(SystemExit) as exc:
            c.preflight_checks()

        assert exc.value.code == 1


@docker
class TestMockPiholeStateDocker:
    """Integration tests verifying mock Pi-hole control endpoints work."""

    def test_set_fail_auth_then_check(self):
        """With fail_auth=true, _check_pihole_api should return False."""
        import json as _json
        import urllib.request

        def _post(url, payload):
            req = urllib.request.Request(
                url,
                data=_json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)

        # Enable fail_auth on primary
        _post(f"{DOCKER_PRIMARY_URL}/mock/set-state", {"fail_auth": True})
        try:
            c = _make_config()
            ok, msg = c._check_pihole_api("localhost:8001", DOCKER_PASSWORD)
            assert ok is False
        finally:
            # Always restore
            _post(f"{DOCKER_PRIMARY_URL}/mock/set-state", {"fail_auth": False})

    def test_primary_reset_restores_auth(self):
        """After reset, primary auth should work again."""
        import json as _json
        import urllib.request

        # Trigger fail then reset
        req = urllib.request.Request(
            f"{DOCKER_PRIMARY_URL}/mock/reset",
            data=b"",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)

        c = _make_config()
        ok, msg = c._check_pihole_api("localhost:8001", DOCKER_PASSWORD)
        assert ok is True
