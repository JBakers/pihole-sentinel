# User TODOs

## Current Status
- **Branch:** develop
- **Version:** 0.12.1-beta.10
- **Last updated:** 2026-03-28 (setup.py full end-to-end working; full notification audit complete)
- **Setup status:** ✅ Full deployment works without errors (tested 2026-03-28)

### Resolved on 2026-03-28 — setup.py

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

### Resolved on 2026-03-28 — notifications

| # | Problem | Fix |
|---|---------|-----|
| 11 | `fault` always showed "Both Pi-holes may have issues!" | Default template now uses `{reason}` |
| 12 | Failover/recovery reason showed "Unknown" | `describe_master_transition()` with full diagnosis |
| 13 | `import time` missing — monitor loop crashed every cycle | Added `import time` |
| 14 | No immediate fault notification before VRRP switch | `send_notification("fault")` on offline/service-down events |
| 15 | Recovery classified as failover with wrong reason | Proper `recovery` event type with `{reason}` variable |
| 16 | Reminders sent with "Unknown" node name | Last `template_vars` stored and reused for reminders |
| 17 | Startup notification never sent | `send_notification("startup")` added to startup block |

---

## 🔴 BUGS — High Priority

### B1. index.html: System Commands JS not inside `<script>` tag
**Location:** `dashboard/index.html` lines ~1090-1210
**Problem:** After the command-modal `</div>` there are ~120 lines of JavaScript directly in the HTML body as raw text (visible to the user). Missing `<script>` and `</script>` tags.
**Impact:** Commands section does not work; JS is visible as text in the footer.

### B2. index.html: System Commands card incorrectly nested in footer div
**Location:** `dashboard/index.html` line ~1030
**Problem:** The System Commands card and modal are **inside** `<div class="footer">` instead of before it. Footer structure is broken.
**Impact:** Footer layout is wrong; commands card styling falls within footer context.

### B3. monitor.py: `/api/commands/{name}` endpoint is MISSING
**Location:** `dashboard/monitor.py`
**Problem:** System Commands in index.html call `POST /api/commands/monitor_status` etc. but no `/api/commands` route exists in monitor.py.
**Impact:** All 6 command buttons return 404/405.

### B4. monitor.py: SnoozeResponse model mismatch → 500 error
**Location:** `dashboard/monitor.py` lines 182-186 vs 1996
**Problem:** Model expects `snoozed` (bool) + `remaining_seconds` (int), but endpoint returns `enabled` + `active`.
**Impact:** `GET /api/notifications/snooze` always returns 500 Internal Server Error.

### B5. monitor.py: DHCP warning spam every monitor cycle
**Location:** `dashboard/monitor.py` lines ~1349-1365
**Problem:** "DHCP misconfiguration" warning is logged as an event every 5s without debounce/dedup.
**Impact:** Events table fills with the same warning 19× within 2 minutes.

### B6. monitor.py: CONFIG key mismatch in failover notification
**Location:** `dashboard/monitor.py` lines ~1305-1310
**Problem:** Uses `CONFIG.get('primary_name')` but CONFIG uses nested dicts: `CONFIG["primary"]["name"]`. Returns `None`.
**Impact:** Notification template variables `{primary}` and `{secondary}` are `None`.

---

## 🟡 BUGS — Medium Priority

### B7. monitor.py: Duplicate "Monitor started" event
**Location:** `dashboard/monitor.py` lines 201 + 1206
**Problem:** "Monitor started" is logged twice: in `lifespan` startup and in `monitor_loop` first iteration.
**Impact:** Two "Monitor started" events on every restart.

### B8. monitor.py: `dhcp_leases` always 0 when no MASTER
**Location:** `dashboard/monitor.py` lines ~1266-1270
**Problem:** Leases are only counted from the MASTER node. When no node is MASTER (VIP down), it is always 0.
**Impact:** Dashboard shows 0 leases while Pi-holes are actively serving leases.

### B9. Dashboard API key hardcoded as `YOUR_API_KEY_HERE`
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

### F2. Debounce DHCP misconfiguration warnings
Log at most once per 5 minutes per node, or only on state change.

### F3. Fallback dhcp_leases when no MASTER
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

### D4. Standardize documentation language
All docs must be in English.

---

## 🟣 pisen CLI Tool — Analysis

### Status: Usable but limited
**Location:** `bin/pisen`

**Strengths:**
- Well-structured with Colors, Config, Commands classes
- 6 useful subcommands: status, logs, vip, dashboard, health, test
- Auto-detects server type (monitor/pihole/unknown)
- Good failover testing guide

**Issues:**
- P1: Hardcoded path to VERSION: `/home/user/Workspace/pihole-sentinel/VERSION` (line 402)
- P2: Requires `systemctl` → does not work in Docker, only on production
- P3: No API client mode (could talk to monitor API over HTTP)
- P4: Copyright hardcoded `2025` → should be dynamic or `2025-2026`

**Recommendation:** Keep and improve. The CLI is useful for production. Add a `--api` mode that talks to the monitor API over HTTP (then also works in Docker). Fix the hardcoded path.

---

## 🐳 Docker Test Environment

### Current status (working)
- 17 containers: 2 mock Pi-holes, 1 monitor, 12 fake clients
- Each Pi-hole sees 15 DHCP leases (3 static + 12 ARP-discovered)
- Unit tests pass
- Mock Pi-holes with ARP auto-discovery

### Known Docker limitations (expected, not bugs)
- **dns: false** — mock Pi-holes do not serve real DNS
- **Both nodes BACKUP** — no keepalived = no VIP
- **No failover events** — no VIP switch = no MASTER change
- **Dashboard 403** — API key not injected (see B9)

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
- **No failover events** — no VIP switch = no MASTER change
- **Dashboard 403** — API key not injected (see B9)

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

---

## Completed Items (2026-02-06)
- [x] Repository cleanup: .gitignore, dead links, stale versions
- [x] License corrected: MIT → GPLv3 in all files
- [x] CHANGELOG.md structure fixed
- [x] CLAUDE.md references to non-existent files cleaned up
- [x] Docker dev files (Dockerfile.dev, docker-compose.test.yml) added to git
- [x] tmp/ directory cleaned up
- [x] docs/README.md consolidated and optimized
- [x] All docs version numbers updated to 0.12.0-beta.9
- [x] Docker test environment extended with 12 fake clients
- [x] Mock Pi-hole ARP auto-discovery for DHCP leases
- [x] `.dockerignore` added
- [x] Makefile extended with docker-status/failover/recover targets
- [x] Full GUI audit (index.html + settings.html + all API endpoints)
- [x] pisen CLI tool audited

---

**Last audit:** 2026-03-28
