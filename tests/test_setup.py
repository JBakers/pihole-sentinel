"""
Tests for setup.py — preflight checks, rollback, and uninstall logic.

Unit tests run without any external dependencies (SSH/Docker mocked).
Integration tests (marked 'docker') require the Docker test environment:
    make docker-up
    pytest -m docker tests/test_setup.py

Docker endpoints used in integration tests:
    Primary mock Pi-hole:   http://localhost:8001  (password: testpass123)
    Secondary mock Pi-hole: http://localhost:8002  (password: testpass123)
"""

import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from setup import SetupConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides):
    """Return a minimal SetupConfig pre-loaded with a test config dict."""
    c = SetupConfig()
    c.config.update({
        "separate_monitor":   True,
        "monitor_ip":         "10.99.0.20",
        "monitor_ssh_user":   "root",
        "monitor_ssh_port":   "22",
        "primary_ip":         "10.99.0.10",
        "primary_ssh_user":   "root",
        "primary_ssh_port":   "22",
        "primary_password":   "testpass123",
        "secondary_ip":       "10.99.0.11",
        "secondary_ssh_user": "root",
        "secondary_ssh_port": "22",
        "secondary_password": "testpass123",
        "ssh_key_path":       None,
        **overrides,
    })
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

        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
                None, 401, "Unauthorized", {}, None)):
            ok, msg = c._check_pihole_api("10.0.0.1", "bad")

        assert ok is False
        assert "401" in msg

    def test_unreachable_host_returns_false(self):
        """Connection refused / timeout → (False, message)."""
        import urllib.error
        c = _make_config()

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            ok, msg = c._check_pihole_api("10.0.0.1", "pass")

        assert ok is False
        assert "unreachable" in msg


# ---------------------------------------------------------------------------
# preflight_checks  (unit)
# ---------------------------------------------------------------------------

class TestPreflightChecks:
    """Unit tests for SetupConfig.preflight_checks()."""

    def test_all_ok_passes(self, capsys):
        """All SSH + API checks pass → no sys.exit."""
        c = _make_config()

        with patch.object(c, "remote_exec") as mock_ssh, \
             patch.object(c, "_check_pihole_api", return_value=(True, "OK")):
            c.preflight_checks()  # must not raise / exit

        # remote_exec called for monitor + primary + secondary (3 SSH checks)
        assert mock_ssh.call_count == 3

    def test_ssh_failure_exits(self, capsys):
        """SSH failure on one host → sys.exit(1)."""
        c = _make_config()

        def ssh_fails(host, user, port, cmd):
            if host == "10.99.0.10":
                raise subprocess.CalledProcessError(255, "ssh")

        with patch.object(c, "remote_exec", side_effect=ssh_fails), \
             patch.object(c, "_check_pihole_api", return_value=(True, "OK")):
            with pytest.raises(SystemExit) as exc:
                c.preflight_checks()

        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "SSH login failed" in out

    def test_api_failure_exits(self, capsys):
        """Wrong Pi-hole password → sys.exit(1)."""
        c = _make_config()

        with patch.object(c, "remote_exec"), \
             patch.object(c, "_check_pihole_api",
                          return_value=(False, "wrong password")):
            with pytest.raises(SystemExit) as exc:
                c.preflight_checks()

        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "wrong password" in out

    def test_multiple_failures_shown_all(self, capsys):
        """Multiple failures are all reported before exiting."""
        c = _make_config()

        with patch.object(c, "remote_exec",
                          side_effect=subprocess.CalledProcessError(255, "ssh")), \
             patch.object(c, "_check_pihole_api",
                          return_value=(False, "wrong password")):
            with pytest.raises(SystemExit):
                c.preflight_checks()

        out = capsys.readouterr().out
        # SSH failures for all 3 hosts + 2 API check failures
        assert out.count("✗") >= 3

    def test_no_separate_monitor_skips_monitor_ssh(self):
        """Without separate monitor, no SSH check for monitor."""
        c = _make_config(separate_monitor=False)

        with patch.object(c, "remote_exec") as mock_ssh, \
             patch.object(c, "_check_pihole_api", return_value=(True, "OK")):
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
            {"type": "monitor",   "host": "10.99.0.20", "user": "root",
             "port": "22", "backup_ts": "20260328_120000"},
            {"type": "primary",   "host": "10.99.0.10", "user": "root",
             "port": "22", "backup_ts": "20260328_120001"},
            {"type": "secondary", "host": "10.99.0.11", "user": "root",
             "port": "22", "backup_ts": "20260328_120002"},
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
        hosts = [{"type": "primary", "host": "10.99.0.10",
                  "user": "root", "port": "22", "backup_ts": None}]
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

        with patch.object(c, "remote_exec",
                          side_effect=lambda h, u, p, cmd: exec_calls.append((h, cmd))), \
             patch("builtins.input", return_value="yes"):
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

        with patch.object(c, "remote_exec",
                          side_effect=lambda h, u, p, cmd: exec_calls.append(cmd)), \
             patch("builtins.input", return_value="yes"):
            c.uninstall()

        all_cmds = " ".join(exec_calls)
        assert "/opt/pihole-monitor" in all_cmds
        assert "/etc/keepalived/keepalived.conf" in all_cmds
        assert "/usr/local/bin/check_pihole_service.sh" in all_cmds
        assert "/usr/local/bin/keepalived_notify.sh" in all_cmds

    def test_uninstall_cancelled_by_user(self, capsys):
        """Input other than 'yes' cancels without touching any server."""
        c = _make_config()

        with patch.object(c, "remote_exec") as mock_exec, \
             patch("builtins.input", return_value="no"):
            c.uninstall()

        mock_exec.assert_not_called()
        out = capsys.readouterr().out
        assert "cancelled" in out.lower()

    def test_uninstall_no_separate_monitor_skips_monitor_host(self):
        """Without separate monitor, pihole-monitor removal targets primary."""
        c = _make_config(separate_monitor=False, monitor_ip=None)
        exec_calls = []

        with patch.object(c, "remote_exec",
                          side_effect=lambda h, u, p, cmd: exec_calls.append((h, cmd))), \
             patch("builtins.input", return_value="yes"):
            c.uninstall()

        # No calls against 10.99.0.20 (monitor-only IP)
        monitor_calls = [h for h, _ in exec_calls if h == "10.99.0.20"]
        assert len(monitor_calls) == 0

    def test_uninstall_tolerates_remote_exec_failure(self):
        """SSH errors during uninstall are reported but don't crash setup."""
        c = _make_config()

        with patch.object(c, "remote_exec",
                          side_effect=Exception("connection refused")), \
             patch("builtins.input", return_value="yes"):
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
# Integration tests — require running Docker environment
# ---------------------------------------------------------------------------

DOCKER_PRIMARY_URL   = "http://localhost:8001"
DOCKER_SECONDARY_URL = "http://localhost:8002"
DOCKER_PASSWORD      = "testpass123"
DOCKER_WRONG_PW      = "definitely-wrong"


def _docker_available():
    """Return True if the Docker mock Pi-holes are reachable."""
    import urllib.request
    import urllib.error
    try:
        urllib.request.urlopen(f"{DOCKER_PRIMARY_URL}/mock/state", timeout=2)
        return True
    except Exception:
        return False


docker = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker test environment not running (make docker-up)"
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
        import urllib.request
        import json as _json
        url = f"{DOCKER_PRIMARY_URL}/api/auth"
        payload = _json.dumps({"password": DOCKER_PASSWORD}).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = _json.loads(resp.read().decode())
        assert body["session"]["valid"] is True

    def test_primary_wrong_password(self):
        import urllib.request
        import urllib.error
        import json as _json
        url = f"{DOCKER_PRIMARY_URL}/api/auth"
        payload = _json.dumps({"password": DOCKER_WRONG_PW}).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        # Mock Pi-hole returns 401 for wrong password
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req, timeout=8)
        assert exc_info.value.code == 401

    def test_secondary_correct_password(self):
        import urllib.request
        import json as _json
        url = f"{DOCKER_SECONDARY_URL}/api/auth"
        payload = _json.dumps({"password": DOCKER_PASSWORD}).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
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
        with patch.object(c, "remote_exec"), \
             pytest.raises(SystemExit) as exc:
            c.preflight_checks()

        assert exc.value.code == 1


@docker
class TestMockPiholeStateDocker:
    """Integration tests verifying mock Pi-hole control endpoints work."""

    def test_set_fail_auth_then_check(self):
        """With fail_auth=true, _check_pihole_api should return False."""
        import urllib.request
        import json as _json

        def _post(url, payload):
            req = urllib.request.Request(
                url, data=_json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"}, method="POST"
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
        import urllib.request
        import json as _json

        # Trigger fail then reset
        req = urllib.request.Request(
            f"{DOCKER_PRIMARY_URL}/mock/reset",
            data=b"", headers={"Content-Type": "application/json"}, method="POST"
        )
        urllib.request.urlopen(req, timeout=5)

        c = _make_config()
        ok, msg = c._check_pihole_api("localhost:8001", DOCKER_PASSWORD)
        assert ok is True
