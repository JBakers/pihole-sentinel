# User TODOs

## Current Status
- **Branch:** `feature/multi-node-support`
- **Version:** `0.20.1`
- **Last updated:** 2026-05-13
- **Core status:** ✅ M1-P1 completed (config, DB migration, polling loop, VIP, debounce)

---

## ✅ Completed This Session

- **M1-P1 Task 1.1:** Dynamic N-node config loading (`PIHOLE_N_*`) with legacy fallback
- **M1-P1 Task 1.2:** New normalized DB schema (`poll_cycles`, `node_status`) + startup migration
- **M1-P1 Task 1.3:** `monitor_loop()` refactored to node-list based processing
- **M1-P1 Task 1.4:** `check_who_has_vip()` generalized for N nodes (legacy 2-node signature preserved)
- **M1-P1 Task 1.5:** Fault/Pi-hole debounce generalized per node key
- **Docker test compose:** Added healthchecks for mock Pi-hole services in `docker-compose.test.yml`

---

## 🔜 Next Work (Recommended Order)

1. **M1-P2:** Migrate API responses to `nodes[]` shape
	- `/api/status`
	- `/api/history`
	- related response models and backward-compat strategy
2. **M1-P3:** Dashboard UI dynamic node rendering
	- remove hardcoded primary/secondary cards
	- dynamic status + chart series per node
3. **M1-P4:** setup.py multi-node wizard/config generation
4. **M1-P5:** Extend integration/docker fixtures for true 3-node scenarios
5. **D2:** Raise monitor.py test coverage target to 60%+

---

## 🧪 Test Status Snapshot

- Full suite in this environment: **564 passed, 28 skipped**
- Skips are environment-dependent:
  - Docker integration/setup tests when Docker environment is not up
  - one Windows-specific chmod skip

---

## Useful Commands

```bash
git checkout feature/multi-node-support
git pull origin feature/multi-node-support

# Full test suite
python -m pytest tests/ -q

# Bring up docker integration environment
docker compose -f docker-compose.test.yml down -v
docker compose -f docker-compose.test.yml up -d --build
docker compose -f docker-compose.test.yml ps

# Run docker-dependent tests
python -m pytest tests/test_integration.py -m integration -vv
```

---

**Last updated:** 2026-05-13
