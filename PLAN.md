# PLAN.md — Pi-hole Sentinel Development Plan

**Last Updated:** 2026-04-15
**Branch:** `develop`
**Current Version:** 0.16.5

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

### Branch: `develop` — v0.16.5

| Item | Status |
|------|--------|
| Core monitoring service (monitor.py) | ✅ Stable |
| Dashboard + Settings UI | ✅ Up to date |
| setup.py deployment (bare-metal) | ✅ Fully working (tested 2026-03-28) |
| Config sync (pihole.toml + gravity) | ✅ Stable |
| Notifications (Telegram/Discord/Pushover/Ntfy) | ✅ Working |
| System Commands panel | ✅ Working |
| Fault debounce + recovery notifications | ✅ Working |
| DHCP auto-detection | ✅ Working (3-poll debounce) |
| Docker integration test suite (16 tests) | ✅ Working (`make docker-integration`) |
| Unit tests | ⚠️ ~20% coverage — needs expansion |
| Container architecture (v2.0) | 🔲 Separate branch: `feature/container-architecture` |

---

## Open Bugs

### � Medium Priority

| ID | Bug | Location | Impact |
|----|-----|----------|--------|
| F4 | DNS mock only binds TCP:53, not UDP | `docker/mock-pihole/mock_pihole.py` | `dig` checks fail in Docker test (uses UDP) |

---

## Open Improvements

| ID | Improvement | Priority |
|----|-------------|----------|
| D2 | Expand test coverage (currently ~20%, target 60%+) | High |
| D3 | HTTPS/reverse proxy documentation (nginx/Caddy example) | Low |
| P2 | `pisen` CLI: make copyright year dynamic | Low |
| P3 | `pisen` CLI: add `--api` mode (HTTP client to monitor API) | Low |

---

## Low Priority / Later

| Task | Details |
|------|---------|
| Prometheus metrics endpoint | `GET /metrics` in monitor.py |
| HTTPS / TLS support | Self-signed cert or Let's Encrypt integration |

| Database auto-cleanup | Delete status_history older than 30 days |

---

## Completed Items

### v0.16.5 (2026-04-15) — Copilot PR review fixes

- [x] `StatusResponse` missing `dhcp_failover` field — added to Pydantic model
- [x] Rate limiter trusted `X-Forwarded-For` unconditionally — requires `TRUST_PROXY_HEADERS=true`
- [x] `setup.py` overwrote `notify_settings.json` on re-deploy — now merges, preserves notification config
- [x] SSH `known_hosts` blocked by `ReadOnlyPaths` in systemd unit — fixed (protect only private key)
- [x] `validate_ip` accepted invalid octets (e.g. 999.x.x.x) — added 0–255 range check
- [x] `DHCP_ENABLED` had no default in `keepalived_notify.sh` — default `true` for backward compat
- [x] Unconditional "Preserved" log messages in sync script — now gated on actual replacement
- [x] Unused `encoded_message` in `notify.sh` — removed dead curl encoding call
- [x] `requests` missing from `requirements-dev.txt` — added for integration tests

### v0.16.2 – v0.16.4 (2026-04-12 – 2026-04-15)

- [x] DHCP auto-detection disabled failover during Pi-hole outage (critical fix)
- [x] Docker integration test suite — 16 e2e tests via `make docker-integration`
- [x] `EVENT_DEBOUNCE_SECONDS` env var configurable (default: 30s)
- [x] DHCP failover default changed from `True` to `False`
- [x] `PiHoleStatus` Pydantic model missing stats fields (queries/blocked/clients)
- [x] Mock Pi-hole reset incomplete — state bleed between tests fixed

### v0.14.1 – v0.16.1 (2026-03-29 – 2026-04-12)

- [x] B1: Duplicate "Monitor started" event — fixed (single log point in monitor_loop)
- [x] B2: `dhcp_leases` always 0 when no MASTER — fallback `max()` of both nodes
- [x] B3: Dashboard API key hardcoded — runtime injection via `<meta>` tag
- [x] B10: LOCAL_SETUP.md completely outdated — rewritten for current Docker setup
- [x] F1: API key runtime injection — `serve_index`/`serve_settings` inject key via meta
- [x] F2: Fallback `dhcp_leases` when no MASTER — implemented
- [x] F5: `/api/commands` endpoint — 6 system commands implemented
- [x] P1: `pisen` CLI hardcoded VERSION path — fixed
- [x] pwhash / upstreams preservation via Python heredocs (no process arg exposure)
- [x] Section-scoped TOML sync (domain, cert, listeningMode)

### v0.12.5-beta.4 – v0.14.0 (2026-03-29)

- [x] SSH deployment with non-root user — all privileged remote commands now use `sudo`
- [x] `_s(user)` helper with `sudo -n` — fails fast instead of hanging without NOPASSWD
- [x] MITM warning printed when SSH keys are generated (StrictHostKeyChecking=no)
- [x] Config sync backup rotation fixed on secondary node (disk full bug)
- [x] `SYNC_MAX_BACKUPS` variable added (default: 3, configurable in sync.conf)

### v0.12.2 (2026-03-28)

- [x] setup.py fully working end-to-end (SSH + Pi-hole preflight checks)
- [x] Automatic rollback on deployment failure
- [x] Fault debounce 60s + paired recovery notifications
- [x] System Commands panel in dashboard
- [x] ANSI colour rendering in command output modal
- [x] Offline indicators (Pi-hole / VIP / DNS / DHCP)

### Earlier (develop branch)

- [x] Repository cleanup: .gitignore, dead links, stale versions
- [x] License corrected: MIT → GPLv3
- [x] Docker test environment (mock Pi-holes + fake clients)
- [x] 217 unit tests passing
- [x] Makefile with full development workflow
- [x] API key authentication on all endpoints
- [x] Rate limiting on all write endpoints
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
make docker-failover        # Simulate primary failure
make docker-recover         # Restore primary
make docker-integration     # Run integration tests (requires docker-up)
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
