# User TODOs

## Current Status
- **Branch:** develop
- **Version:** 0.12.2-beta.4
- **Last updated:** 2026-03-28
- **Setup status:** ✅ Full deployment works without errors (tested 2026-03-28)

---

## ✅ Resolved on 2026-03-28 — setup.py

| # | Problem | Fix |
|---|---------|-----|
| 1 | `dnsutils` always "missing" on Debian 13 | `dpkg-query` + `bind9-dnsutils` fallback |
| 2 | DHCP/FTL restart loop (`dhcp_control.sh`) | Check current state before FTL restart |
| 3 | keepalived would not start: wrong interface | Auto-detect via `ip route get 8.8.8.8` after deploy |
| 4 | keepalived auth_pass truncated (32→8 chars) | `generate_secure_password(length=8)` |
| 5 | keepalived failure diagnosis not visible | `--config-test` + full journal in output |
| 6 | VRRP v3 + auth = exit code 1 | `vrrp_version 2` in all templates |
| 7 | `preempt_delay` on MASTER = exit code 1 | Removed from MASTER template |
| 8 | No pre-flight check | `preflight_checks()`: SSH + Pi-hole API before deploy |
| 9 | No rollback on failure | `rollback_deployment()` + backup-timestamp tracking |
| 10 | No uninstall option | Menu option 6: full uninstall via SSH |
| 11 | SSH disconnect (exit 255) right after uninstall | `remote_exec` retries 3× with 10 s delay + ConnectTimeout=30 |

## ✅ Resolved on 2026-03-28 — notifications & dashboard

| # | Problem | Fix |
|---|---------|-----|
| 12 | `fault` always showed "Both Pi-holes may have issues!" | Default template now uses `{reason}` |
| 13 | Failover/recovery reason showed "Unknown" | `describe_master_transition()` with full diagnosis |
| 14 | `import time` missing — monitor loop crashed every cycle | Added `import time` |
| 15 | Recovery classified as failover with wrong reason | Proper `recovery` event type with `{reason}` variable |
| 16 | Reminders sent with "Unknown" node name | Last `template_vars` stored and reused for reminders |
| 17 | Startup notification never sent | `send_notification("startup")` added to startup block |
| 18 | Fault notification every ~20 min (brief FTL restart) | 60 s debounce via `_arm_fault` / `_cancel_fault` |
| 19 | No recovery notification after fault was sent | `_fault_notified` set + async `_cancel_fault` sends `recovery` |
| 20 | Test notification showed "Failed: Unknown error" despite delivery | Response matches Pydantic model `{success, service, message}` |
| 21 | System Commands modal showed "undefined undefined" | API returns `{icon, description, exit_code, status, output}` |
| 22 | Recent Events limited to 20 lines, not scrollable | Limit → 500, oldest→newest, modal max-height 65 vh |
| 23 | Failover History only showed failovers, not recoveries | Filter includes `event_type='recovery'`; green tint + ✅ prefix |

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
