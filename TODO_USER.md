# User TODOs

## Current Status
- **Branch:** develop
- **Version:** 0.16.5
- **Last updated:** 2026-04-15
- **Setup status:** ✅ Full deployment works without errors (tested 2026-03-28)

> All items resolved up to and including v0.16.5 are documented in [CHANGELOG.md](CHANGELOG.md).

---

## � BUGS — Medium Priority

### F4. DNS mock only uses TCP:53, not UDP
**Location:** `docker/mock-pihole/mock_pihole.py`
**Problem:** Mock Pi-hole binds a TCP listener on port 53, but `monitor.py` uses `dig @{ip} example.com` which defaults to UDP. DNS checks therefore always fail in the Docker test environment.
**Impact:** DNS check shown as failing in Docker test. Not an issue in production.

---

## 🔵 Improvements — Documentation & Tooling

### D2. Expand test coverage
**Current coverage:** ~20% (unit tests only). Missing: async operations, database, notifications, API handlers with real HTTP.

### D3. Document HTTPS/reverse proxy setup
Nginx/Caddy example for production HTTPS.

---

## 🟣 pisen CLI Tool

### Status: Usable
**Location:** `bin/pisen`

**Open issues:**
- P2: Copyright year hardcoded `2025` → should be dynamic or `2025-2026`
- P3: No API client mode (could talk to monitor API over HTTP)

---

## 🐳 Docker Test Environment

### Current status (working)
- Containers: 2 mock Pi-holes, 1 monitor, fake clients
- 16 integration tests available via `make docker-integration`
- API key injection works (runtime meta tag)

### Known Docker limitations (expected, not bugs)
- Both nodes BACKUP — no keepalived = no VIP
- DNS checks fail — mock uses TCP:53, `dig` needs UDP (see F4 above)

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

**Last updated:** 2026-04-15
