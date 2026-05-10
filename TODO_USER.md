# User TODOs

## Current Status
- **Branch:** develop
- **Version:** 0.18.5
- **Last updated:** 2026-05-10
- **Setup status:** ✅ Full deployment works without errors (tested 2026-03-28)

> All items resolved up to and including v0.16.7 are documented in [CHANGELOG.md](CHANGELOG.md).

---

## ✅ Bugs — All Resolved

No open bugs. See [CHANGELOG.md](CHANGELOG.md) for history.

---

## 🔵 Improvements — Documentation & Tooling

### D2. Expand test coverage
**Current coverage:** 54% on monitor.py (399 tests, 17 files). Remaining gaps: async `monitor_loop`, rate-limit middleware, API endpoints (`/api/history`, `/api/events`, execute_command).

---

## 🟣 pisen CLI Tool

### Status: Usable
**Location:** `bin/pisen`

**Resolved issues:**
- ✅ P2: Copyright year now dynamic (`2025-{year}`) — fixed in v0.18.0
- ✅ P3: `pisen api` command added — fetches live status from monitor API over HTTP (v0.18.0)

---

## 🐳 Docker Test Environment

### Current status (working)
- Containers: 2 mock Pi-holes, 1 monitor, fake clients
- 20 integration tests available via `make docker-integration`
- API key injection works (runtime meta tag)

### Known Docker limitations (expected, not bugs)
- Both nodes BACKUP — no keepalived = no VIP

### Useful commands
```bash
make docker-up              # Start full environment
make docker-down            # Stop + cleanup
make docker-status          # Status overview
make docker-failover        # Simulate primary failure
make docker-recover         # Restore primary
make docker-integration     # Run integration tests
make docker-logs            # Live logs
```

---

**Last updated:** 2026-05-10
