# User TODOs

## Current Status
- **Branch:** develop
- **Version:** 0.12.4-beta.7
- **Last updated:** 2026-03-28
- **Setup status:** ✅ Full deployment works without errors (tested 2026-03-28)

> All items resolved up to and including v0.12.2-beta.8 are documented in [CHANGELOG.md](CHANGELOG.md).

---

## 🔴 BUGS — High Priority

### B1. monitor.py: Duplicate "Monitor started" event
**Location:** `dashboard/monitor.py` lines 201 + 1206
**Problem:** "Monitor started" is logged twice: in `lifespan` startup and in `monitor_loop` first iteration.
**Impact:** Two "Monitor started" events on every restart.

### B2. monitor.py: `dhcp_leases` always 0 when no MASTER
**Location:** `dashboard/monitor.py` lines ~1266-1270
**Problem:** Leases are only counted from the MASTER node. When no node is MASTER (VIP down), it is always 0.
**Impact:** Dashboard shows 0 leases while Pi-holes are actively serving leases.

### B3. Dashboard API key hardcoded as `YOUR_API_KEY_HERE`
**Location:** `dashboard/index.html` line 1226, `dashboard/settings.html` line 1101
**Problem:** `setup.py` replaces this with `sed` on deploy, but in Docker test nothing works. No runtime injection mechanism.
**Impact:** Dashboard returns 403 on every API call in Docker test. Only usable after `setup.py` deploy.

### B10. LOCAL_SETUP.md completely outdated
**Location:** `LOCAL_SETUP.md`
**Problem:** References old `172.20.0.x` subnet, `docker-compose` v1, Redis container, `python:3.14-slim`. No longer matches `docker-compose.test.yml`.
**Impact:** Misleading documentation for contributors.

---

## 🟢 Improvements — Functionality

### F1. API key runtime injection for Docker test
Change `serve_index()`/`serve_settings()` to replace `YOUR_API_KEY_HERE` at runtime with `CONFIG["api_key"]`. Dashboard then works directly in Docker without `sed`.

### F2. Fallback dhcp_leases when no MASTER
When no node is MASTER, count leases from the node with `dhcp_enabled=True`.

### F4. DNS mock in mock_pihole.py
Add lightweight UDP DNS server (port 53, always answer 1.2.3.4) so DNS checks pass in Docker.

### F5. Implement `/api/commands` endpoint
6 commands: `monitor_status`, `monitor_logs`, `keepalived_status`, `keepalived_logs`, `vip_check`, `db_recent_events`. Use subprocess with timeout and output capture.

---

## 🔵 Improvements — Documentation & Tooling

### D1. Rewrite LOCAL_SETUP.md
Update to current Docker setup: `10.99.0.x` subnet, fake clients, `docker compose` v2, no Redis. Point to `make docker-up`.

### D2. Expand test coverage
**Current coverage:** ~20% (unit tests only). Missing: async operations, database, notifications, API handlers with real HTTP.

### D3. Document HTTPS/reverse proxy setup
Nginx/Caddy example for production HTTPS.

---

## 🟣 pisen CLI Tool — Analysis

### Status: Usable but limited
**Location:** `bin/pisen`

**Issues:**
- P1: Hardcoded path to VERSION: `/home/jochem/Workspace/pihole-sentinel/VERSION` (line 402)
- P2: Requires `systemctl` → does not work in Docker, only on production
- P3: No API client mode (could talk to monitor API over HTTP)
- P4: Copyright hardcoded `2025` → should be dynamic or `2025-2026`

**Recommendation:** Fix P1 (hardcoded path) and P4 (year). Add a `--api` mode.

---

## 🐳 Docker Test Environment

### Current status (working)
- 17 containers: 2 mock Pi-holes, 1 monitor, 12 fake clients
- Each Pi-hole sees 15 DHCP leases (3 static + 12 ARP-discovered)
- Unit tests pass

### Known Docker limitations (expected, not bugs)
- Both nodes BACKUP — no keepalived = no VIP
- No failover events — no VIP switch = no MASTER change
- Dashboard 403 — API key not injected (see B3)

### Useful commands
```bash
make docker-up        # Start full environment (17 containers)
make docker-down      # Stop + cleanup
make docker-status    # Status overview
make docker-failover  # Simulate primary failure
make docker-recover   # Restore primary
make docker-test      # Smoke tests
make docker-logs      # Live logs
```

- [x] Full GUI audit (index.html + settings.html + all API endpoints)
- [x] pisen CLI tool audited

---

**Last audit:** 2026-03-28
