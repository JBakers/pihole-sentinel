# PLAN.md — Pi-hole Sentinel Development Plan

**Last Updated:** 2026-03-29
**Branch:** `develop`
**Current Version:** 0.12.5-beta.7

> **📌 This is the central planning and TODO document.**
> CLAUDE.md references this file. All open tasks, bugs, and the
> development plan are tracked here. Keep this file up to date each session.

---

## Table of Contents

- [Current Status](#current-status)
- [Open Bugs](#open-bugs)
- [Open Improvements](#open-improvements)
- [Low Priority / Later](#low-priority--later)
- [Completed Items](#completed-items)
- [Command Reference](#command-reference)

---

## Current Status

### Branch: `develop` — v0.12.5-beta.7

| Item | Status |
|------|--------|
| Core monitoring service (monitor.py) | ✅ Stable |
| Dashboard + Settings UI | ✅ Up to date |
| setup.py deployment (bare-metal) | ✅ Fully working (tested 2026-03-28) |
| setup.py non-root SSH user support | ✅ Working (beta.4–beta.5) |
| Config sync backup rotation | ✅ Fixed (beta.6) |
| Notifications (Telegram/Discord/Pushover/Ntfy) | ✅ Working |
| System Commands panel | ✅ Working |
| Fault debounce + recovery notifications | ✅ Working |
| Unit tests | ⚠️ ~20% coverage — needs expansion |
| Container architecture (v2.0) | 🔲 Separate branch: `feature/container-architecture` |

---

## Open Bugs

### 🔴 High Priority

| ID | Bug | Location | Impact |
|----|-----|----------|--------|
| B1 | Duplicate "Monitor started" event | `dashboard/monitor.py` L201+1206 | Two events logged on every restart |
| B2 | `dhcp_leases` always 0 when no MASTER | `dashboard/monitor.py` ~L1266 | Dashboard shows 0 leases |
| B3 | Dashboard API key hardcoded `YOUR_API_KEY_HERE` | `dashboard/index.html` L1226, `settings.html` L1101 | 403 on every API call in Docker test |

### 🟡 Medium Priority

| ID | Bug | Location | Impact |
|----|-----|----------|--------|
| B4 | LOCAL_SETUP.md references old subnet / Docker v1 setup | `LOCAL_SETUP.md` | Misleading docs for contributors |

---

## Open Improvements

| ID | Improvement | Priority |
|----|-------------|----------|
| F1 | API key runtime injection for Docker (`serve_index` replaces placeholder) | Medium |
| F2 | Debounce DHCP misconfiguration warnings in monitor.py | Medium |
| F3 | Fallback `dhcp_leases` when no MASTER node | Low |
| F4 | DNS mock in mock_pihole.py (answer UDP:53 queries) | Low |
| D1 | Rewrite LOCAL_SETUP.md for current Docker setup | Medium |
| D2 | Expand test coverage (currently ~20%, target 60%+) | High |
| D3 | HTTPS/reverse proxy documentation (nginx/Caddy example) | Low |
| P1 | `pisen` CLI: fix hardcoded VERSION path | Medium |
| P2 | `pisen` CLI: make copyright year dynamic | Low |

---

## Low Priority / Later

| Task | Details |
|------|---------|
| Prometheus metrics endpoint | `GET /metrics` in monitor.py |
| HTTPS / TLS support | Self-signed cert or Let's Encrypt integration |
| `pisen` CLI `--api` mode | HTTP client to monitor API (works in Docker) |
| Database auto-cleanup | Delete status_history older than 30 days |

---

## Completed Items

### v0.12.5-beta.4 – beta.7 (2026-03-29)

- [x] SSH deployment with non-root user — all privileged remote commands now use `sudo`
- [x] `_s(user)` helper with `sudo -n` — fails fast instead of hanging without NOPASSWD
- [x] MITM warning printed when SSH keys are generated (StrictHostKeyChecking=no)
- [x] apt-get update error visibility — stderr no longer suppressed
- [x] Config sync backup rotation fixed on secondary node (disk full bug)
- [x] `SYNC_MAX_BACKUPS` variable added (default: 3, configurable in sync.conf)

### v0.12.2 (2026-03-28)

- [x] setup.py fully working end-to-end (SSH + Pi-hole preflight checks)
- [x] Automatic rollback on deployment failure
- [x] Fault debounce 60s + paired recovery notifications
- [x] System Commands panel in dashboard
- [x] ANSI colour rendering in command output modal
- [x] Offline indicators (Pi-hole / VIP / DNS / DHCP)
- [x] Failover History shows recovery events as well
- [x] Test notification response Pydantic mismatch fixed
- [x] All Dutch UI strings translated to English

### Earlier (develop branch)

- [x] Repository cleanup: .gitignore, dead links, stale versions
- [x] License corrected: MIT → GPLv3
- [x] Docker test environment (mock Pi-holes + fake clients)
- [x] 141 unit tests passing
- [x] Makefile with full development workflow
- [x] API key authentication on all endpoints
- [x] Rate limiting on test-notification endpoint
- [x] VIP detection retry logic (3×)

### Container Architecture (feature branch)

- [x] Keepalived sidecar PoC (VRRP election + VIP in Docker proven)
- [x] Sentinel-node container (keepalived + FastAPI sync agent on port 5000)
- [x] docker-compose.poc.yml (2 mock Pi-holes + 2 sentinel-nodes)
- [x] Sync agent endpoints: `/health`, `/state`, `/sync/gravity`, `/sync/status`

---

## Command Reference

### Development (local)

```bash
source venv/bin/activate
make test             # Run all unit tests
make test-cov         # With HTML coverage report (htmlcov/)
make lint             # Code quality checks
make format           # Auto-format with black + isort
```

### Docker test environment

```bash
make docker-up        # Start environment (mock Pi-holes + clients)
make docker-down      # Stop + cleanup
make docker-status    # Status overview
make docker-logs      # Live logs
make docker-failover  # Simulate primary failure
make docker-recover   # Restore primary
```

### Container architecture PoC (feature branch)

```bash
git checkout feature/container-architecture
make poc              # Build + start (4 containers: 2 Pi-holes + 2 sentinel-nodes)
make poc-logs         # Live logs
make poc-down         # Stop + cleanup

# Test endpoints
curl http://localhost:5001/health
curl -H "X-Sync-Token: test-sync-token-12345" http://localhost:5001/sync/status
```

---

**📌 CLAUDE.md references this file for all planning and TODOs.**
