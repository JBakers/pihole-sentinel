#!/usr/bin/env python3
"""
Mock Pi-hole v6 API Server

Simulates Pi-hole v6 API endpoints for testing Pi-hole Sentinel.
Responds to the same endpoints that monitor.py calls:
  - POST /api/auth        (login)
  - GET  /api/stats/summary
  - GET  /api/config/dhcp
  - GET  /api/dhcp/leases
  - DELETE /api/auth      (logout)

Also provides control endpoints to simulate failures:
  - POST /mock/set-state     (set pihole online/offline, dhcp on/off, etc.)
  - GET  /mock/state         (get current mock state)
  - POST /mock/fail-next     (make next N requests fail)

Environment variables:
  - PIHOLE_NAME: Name of this mock (default: "Mock Pi-hole")
  - PIHOLE_PASSWORD: Password for auth (default: "testpass123")
  - DHCP_ENABLED: Start with DHCP enabled (default: "true")
  - IS_PRIMARY: Whether this is the primary server (default: "true")
"""

import os
import json
import uuid
import time
import socket
import threading
import random
import logging
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("mock-pihole")

# Configuration
PIHOLE_NAME = os.getenv("PIHOLE_NAME", "Mock Pi-hole")
PIHOLE_PASSWORD = os.getenv("PIHOLE_PASSWORD", "testpass123")
DHCP_ENABLED = os.getenv("DHCP_ENABLED", "true").lower() == "true"
IS_PRIMARY = os.getenv("IS_PRIMARY", "true").lower() == "true"
PORT = int(os.getenv("PORT", "80"))

# Mutable state
state = {
    "online": True,
    "pihole_running": True,
    "dhcp_enabled": DHCP_ENABLED,
    "dns_working": True,
    "fail_next": 0,  # number of next requests to fail
    "fail_auth": False,
    "response_delay": 0,  # ms delay before response
    "sessions": {},  # active sessions
    "stats": {
        "queries": {
            "total": random.randint(5000, 50000),
            "blocked": random.randint(500, 5000),
        },
        "clients": {
            "total": random.randint(5, 30),
        },
    },
    "leases": [
        {
            "ip": "192.168.1.100",
            "mac": "AA:BB:CC:DD:EE:01",
            "hostname": "desktop-pc",
            "expires": int(time.time()) + 86400,
        },
        {
            "ip": "192.168.1.101",
            "mac": "AA:BB:CC:DD:EE:02",
            "hostname": "laptop",
            "expires": int(time.time()) + 86400,
        },
        {
            "ip": "192.168.1.102",
            "mac": "AA:BB:CC:DD:EE:03",
            "hostname": "phone",
            "expires": int(time.time()) + 43200,
        },
    ],
    "auto_discover_leases": True,  # auto-discover network neighbors as DHCP leases
}

# Device names for auto-discovered clients
_DEVICE_NAMES = [
    "desktop-pc", "laptop", "phone", "tablet", "smart-tv", "printer",
    "gaming-console", "smart-speaker", "thermostat", "doorbell",
    "security-cam", "nas-server", "media-player", "robot-vacuum",
    "smart-plug", "light-hub", "baby-monitor", "garage-opener",
]
_ip_hostname_map = {}  # cache: ip → hostname


def discover_arp_leases() -> list:
    """Discover network neighbors via ARP table and return as DHCP leases.

    Reads `ip neigh show` output, filters for REACHABLE/STALE entries on the
    Docker bridge subnet, and returns them as Pi-hole v6 style lease objects.
    Excludes the gateway (.1) and well-known infra IPs (.10, .11, .20, .100).
    """
    try:
        result = subprocess.run(
            ["ip", "neigh", "show"],
            capture_output=True, text=True, timeout=5
        )
        leases = []
        exclude_ips = {"10.99.0.1", "10.99.0.10", "10.99.0.11", "10.99.0.20", "10.99.0.100"}

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            ip = parts[0]

            # Only include 10.99.0.x subnet, skip infra IPs
            if not ip.startswith("10.99.0.") or ip in exclude_ips:
                continue

            # Extract MAC if present
            try:
                lladdr_idx = parts.index("lladdr")
                mac = parts[lladdr_idx + 1].upper()
            except (ValueError, IndexError):
                continue

            # Assign a stable hostname
            if ip not in _ip_hostname_map:
                idx = len(_ip_hostname_map) % len(_DEVICE_NAMES)
                _ip_hostname_map[ip] = _DEVICE_NAMES[idx]

            leases.append({
                "ip": ip,
                "mac": mac,
                "hostname": _ip_hostname_map[ip],
                "expires": int(time.time()) + 86400,
            })

        return leases
    except Exception as e:
        logger.debug(f"ARP discovery failed: {e}")
        return []


class MockPiholeHandler(BaseHTTPRequestHandler):
    """HTTP request handler simulating Pi-hole v6 API."""

    def log_message(self, format, *args):
        logger.info(f"{self.client_address[0]} - {format % args}")

    def _should_fail(self):
        """Check if this request should fail (for testing error handling)."""
        if not state["online"]:
            self.send_error(503, "Service Unavailable")
            return True
        if state["fail_next"] > 0:
            state["fail_next"] -= 1
            self.send_error(500, "Simulated failure")
            return True
        return False

    def _send_json(self, data, status=200):
        """Send a JSON response."""
        if state["response_delay"] > 0:
            time.sleep(state["response_delay"] / 1000)
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        """Read and parse JSON request body."""
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def _check_auth(self):
        """Verify session authentication. Returns True if valid."""
        sid = self.headers.get("X-FTL-SID", "")
        if sid not in state["sessions"]:
            self._send_json({"error": "Unauthorized"}, 401)
            return False
        return True

    # ─── Pi-hole v6 API ───────────────────────────────────────────

    def do_GET(self):
        path = urlparse(self.path).path

        if self._should_fail():
            return

        # Pi-hole API endpoints
        if path == "/api/stats/summary":
            if not self._check_auth():
                return
            if not state["pihole_running"]:
                self._send_json({"error": "FTL not running"}, 503)
                return
            self._send_json(state["stats"])

        elif path == "/api/config/dhcp":
            if not self._check_auth():
                return
            self._send_json({
                "config": {
                    "dhcp": {
                        "active": state["dhcp_enabled"],
                        "start": "192.168.1.100",
                        "end": "192.168.1.250",
                        "router": "192.168.1.1",
                        "domain": "lan",
                        "leaseTime": "24h",
                        "ipv6": False,
                        "rapidCommit": True,
                    }
                }
            })

        elif path == "/api/dhcp/leases":
            if not self._check_auth():
                return
            # Auto-discover network neighbors as leases if enabled
            if state["auto_discover_leases"]:
                discovered = discover_arp_leases()
                all_leases = state["leases"] + discovered
            else:
                all_leases = state["leases"]
            self._send_json({"leases": all_leases})

        # Mock control endpoints
        elif path == "/mock/state":
            discovered = discover_arp_leases() if state["auto_discover_leases"] else []
            self._send_json({
                "name": PIHOLE_NAME,
                "is_primary": IS_PRIMARY,
                "online": state["online"],
                "pihole_running": state["pihole_running"],
                "dhcp_enabled": state["dhcp_enabled"],
                "dns_working": state["dns_working"],
                "fail_next": state["fail_next"],
                "active_sessions": len(state["sessions"]),
                "stats": state["stats"],
                "leases_static": len(state["leases"]),
                "leases_discovered": len(discovered),
                "leases_total": len(state["leases"]) + len(discovered),
            })

        elif path == "/api/version":
            # Pi-hole version endpoint (not authenticated)
            self._send_json({
                "version": "v6.0.3",
                "branch": "main",
                "date": "2025-01-15",
            })

        elif path == "/admin":
            # Serve a simple Pi-hole admin page
            body = f"<h1>Mock Pi-hole Admin - {PIHOLE_NAME}</h1>".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_error(404, f"Not Found: {path}")

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/auth":
            # Pi-hole login
            if self._should_fail():
                return
            body = self._read_body()
            password = body.get("password", "")

            if state["fail_auth"]:
                self._send_json({"error": "Authentication failed"}, 401)
                return

            if password != PIHOLE_PASSWORD:
                self._send_json({
                    "session": {"valid": False, "sid": None}
                }, 401)
                return

            sid = str(uuid.uuid4())
            state["sessions"][sid] = {
                "created": time.time(),
                "ip": self.client_address[0],
            }
            logger.info(f"Session created: {sid[:8]}... for {self.client_address[0]}")
            self._send_json({
                "session": {
                    "valid": True,
                    "sid": sid,
                    "validity": 300,
                    "message": "Logged in",
                }
            })

        elif path == "/mock/set-state":
            # Control endpoint to change mock state
            body = self._read_body()
            changed = []
            for key in ["online", "pihole_running", "dhcp_enabled", "dns_working",
                        "fail_auth", "response_delay", "auto_discover_leases"]:
                if key in body:
                    state[key] = body[key]
                    changed.append(f"{key}={body[key]}")

            if "stats" in body:
                state["stats"].update(body["stats"])
                changed.append("stats updated")

            if "leases" in body:
                state["leases"] = body["leases"]
                changed.append(f"leases={len(body['leases'])}")

            logger.info(f"State changed: {', '.join(changed)}")
            self._send_json({"status": "ok", "changed": changed})

        elif path == "/mock/fail-next":
            body = self._read_body()
            state["fail_next"] = body.get("count", 1)
            logger.info(f"Will fail next {state['fail_next']} request(s)")
            self._send_json({"status": "ok", "fail_next": state["fail_next"]})

        elif path == "/mock/reset":
            # Reset stats and sessions
            state["sessions"].clear()
            state["fail_next"] = 0
            state["fail_auth"] = False
            state["response_delay"] = 0
            state["online"] = True
            state["pihole_running"] = True
            state["dns_working"] = True
            state["dhcp_enabled"] = os.environ.get("DHCP_ENABLED", "true").lower() == "true"
            state["stats"]["queries"]["total"] = random.randint(5000, 50000)
            state["stats"]["queries"]["blocked"] = random.randint(500, 5000)
            state["stats"]["clients"]["total"] = random.randint(5, 30)
            logger.info("Mock state reset to defaults")
            self._send_json({"status": "ok", "message": "State reset"})

        else:
            self.send_error(404, f"Not Found: {path}")

    def do_DELETE(self):
        path = urlparse(self.path).path

        if path == "/api/auth":
            # Pi-hole logout
            sid = self.headers.get("X-FTL-SID", "")
            if sid in state["sessions"]:
                del state["sessions"][sid]
                logger.info(f"Session deleted: {sid[:8]}...")
            self._send_json({"status": "success"})
        else:
            self.send_error(404, f"Not Found: {path}")


def main():
    logger.info(f"Starting Mock Pi-hole v6 API Server")
    logger.info(f"  Name:     {PIHOLE_NAME}")
    logger.info(f"  Primary:  {IS_PRIMARY}")
    logger.info(f"  DHCP:     {DHCP_ENABLED}")
    logger.info(f"  Password: {'*' * len(PIHOLE_PASSWORD)}")
    logger.info(f"  Port:     {PORT}")
    logger.info(f"")
    logger.info(f"Pi-hole v6 API endpoints:")
    logger.info(f"  POST   /api/auth           - Login")
    logger.info(f"  GET    /api/stats/summary   - Statistics")
    logger.info(f"  GET    /api/config/dhcp     - DHCP config")
    logger.info(f"  GET    /api/dhcp/leases     - DHCP leases")
    logger.info(f"  DELETE /api/auth            - Logout")
    logger.info(f"")
    logger.info(f"Control endpoints:")
    logger.info(f"  GET    /mock/state          - View state")
    logger.info(f"  POST   /mock/set-state      - Change state")
    logger.info(f"  POST   /mock/fail-next      - Simulate failures")
    logger.info(f"  POST   /mock/reset          - Reset to defaults")

    server = HTTPServer(("0.0.0.0", PORT), MockPiholeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()


def build_dns_response(query: bytes) -> bytes:
    """Build a minimal DNS response for A queries.

    Returns a NOERROR response with A record 1.2.3.4 when dns_working is True,
    otherwise returns SERVFAIL without answers.
    """
    if len(query) < 12:
        return b""

    transaction_id = query[:2]
    qdcount = query[4:6]

    # Parse first question section to mirror it in the response.
    idx = 12
    max_len = len(query)
    while idx < max_len:
        label_len = query[idx]
        idx += 1
        if label_len == 0:
            break
        idx += label_len
    # Need QTYPE + QCLASS
    if idx + 4 > max_len:
        return b""
    question = query[12:idx + 4]

    if not state["dns_working"]:
        # Standard query response + recursion available + SERVFAIL
        flags = b"\x81\x82"
        return transaction_id + flags + qdcount + b"\x00\x00\x00\x00\x00\x00" + question

    # Standard query response + recursion available + NOERROR
    flags = b"\x81\x80"
    ancount = b"\x00\x01"
    header = transaction_id + flags + qdcount + ancount + b"\x00\x00\x00\x00"

    # Name pointer to question (0xC00C), A, IN, TTL 60, RDLENGTH 4, RDATA 1.2.3.4
    answer = b"\xC0\x0C\x00\x01\x00\x01\x00\x00\x00\x3C\x00\x04\x01\x02\x03\x04"
    return header + question + answer


def start_mock_dns():
    """Start DNS listeners on port 53 (UDP + TCP).

    - UDP serves minimal DNS responses for `dig` checks used by monitor.py
    - TCP keeps compatibility with previous basic health checks
    """
    def run_udp():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", 53))
            logger.info("Mock DNS (UDP 53) listening")
            while True:
                data, addr = sock.recvfrom(512)
                if not state["online"] or not state["pihole_running"]:
                    continue
                if state["response_delay"] > 0:
                    time.sleep(state["response_delay"] / 1000)
                response = build_dns_response(data)
                if response:
                    sock.sendto(response, addr)
        except Exception as e:
            logger.error(f"Failed to bind UDP 53: {e}")

    def run_tcp():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", 53))
            sock.listen(5)
            logger.info("Mock DNS (TCP 53) listening")
            while True:
                conn, addr = sock.accept()
                conn.close()
        except Exception as e:
            logger.error(f"Failed to bind TCP 53: {e}")

    t_udp = threading.Thread(target=run_udp, daemon=True)
    t_udp.start()

    t = threading.Thread(target=run_tcp, daemon=True)
    t.start()


if __name__ == "__main__":
    start_mock_dns()
    main()
