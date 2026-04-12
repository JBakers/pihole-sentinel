# Testing Guide

**Last Updated:** 2026-03-28
**Current Tests:** 176 (7 test files)
**Coverage:** ~4% (unit tests only, no async/DB coverage yet)

> This document consolidates the former TESTING_WORKFLOW.md and TEST_COVERAGE_PLAN.md
> into a single testing reference.

---

## Quick Start

```bash
source venv/bin/activate
make test             # Run all tests with coverage
make test-cov         # HTML coverage report (htmlcov/)
make lint             # Code quality (pylint, flake8)
make format           # Auto-format (black, isort)
```

---

## Test Suite Overview

### Current Test Files

| File | Tests | Coverage Area |
|------|-------|---------------|
| `test_validation.py` | 24 | Input validation, injection prevention |
| `test_api_handlers.py` | 26 | Pi-hole API calls, response handling |
| `test_dhcp_parsing.py` | 26 | DHCP config parsing, state detection |
| `test_vip_detection.py` | 16 | VIP location, MAC extraction, ARP |
| `test_error_handling.py` | — | Custom exceptions, error handlers |
| `test_notification_transitions.py` | — | Notification state machine |
| `test_setup.py` | 30 | setup.py deployment logic |

### Well Tested

- Input validation (IP, subnet, interface, port, username)
- Injection attack prevention (SQL, XSS)
- DHCP configuration parsing and state detection
- VIP/MAC detection logic
- Pi-hole API authentication

### Not Yet Tested (Gaps)

- Async operations in monitor.py (monitor loop, notifications)
- Database operations (SQLite init, queries, cleanup)
- API endpoint responses (Pydantic models, full HTTP cycle)
- Configuration edge cases (missing env vars, corrupted JSON)
- HTTP timeout and retry scenarios
- Notification delivery (Telegram, Discord, Pushover, Ntfy)

---

## Test Architecture

```
                    ▲
                   / Manual    \   Failover, DHCP, browser compat
                  /  Tests      \
                 ▲               ▼
                / Integration    \   API endpoints, async ops, DB
               /  Tests          \
              ▲                   ▼
             / Unit Tests         \   Validation, models, handlers
            / (176 tests)          \
           ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▼
           Automated & Fast (CI/CD)
```

---

## Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_validation.py -v

# Specific test class
pytest tests/test_error_handling.py::TestExceptionHierarchy -v

# With print output visible
pytest tests/test_setup.py -s

# With debugger on failure
pytest tests/test_vip_detection.py --pdb

# Only async tests
pytest -m asyncio

# Coverage report
pytest --cov=dashboard --cov=setup --cov-report=html
```

---

## Automated Quality Scripts

Located in `.github/scripts/`:

| Script | Purpose |
|--------|---------|
| `run-all-tests.sh` | Master runner: syntax + quality + security |
| `run-syntax-checks.sh` | Python & Bash syntax validation |
| `run-quality-checks.sh` | print() statements, CRLF, required files |
| `run-security-scans.sh` | Hardcoded secrets, bandit, permissions |
| `test-failover.sh` | VIP, master/backup, DNS/DHCP failover |
| `test-dashboard.sh` | API endpoint validation |
| `generate-test-summary.sh` | Markdown test report |
| `nightly-tests.sh` | Automated nightly cron runner |

```bash
# Run all quality checks
./.github/scripts/run-all-tests.sh

# Failover test (requires deployed environment)
./.github/scripts/test-failover.sh <VIP> <primary_ip> <secondary_ip>

# Dashboard API test
./.github/scripts/test-dashboard.sh <monitor_ip> <api_key>
```

---

## Coverage Improvement Plan

### Priority Gaps

| Gap | Area | Priority | Est. Effort |
|-----|------|----------|-------------|
| 1 | Error handling (custom exceptions) | HIGH | 4h |
| 2 | API endpoint responses (Pydantic) | HIGH | 6h |
| 3 | Security hardening (rate limit, CORS) | HIGH | 3h |
| 4 | Async operations (monitor loop, notifications) | HIGH | 8h |
| 5 | Configuration edge cases | MEDIUM | 3h |
| 6 | Database operations (SQLite) | MEDIUM | 4h |

**Total: ~28 hours to reach 60%+ coverage target**

### Coverage Targets

| Module | Current | Target |
|--------|---------|--------|
| `dashboard/monitor.py` | ~4% | 60% |
| `setup.py` | ~4% | 60% |
| Overall | ~4% | 60%+ |

### Test Infrastructure

- **pytest** — Test runner
- **pytest-asyncio** — Async test support
- **pytest-cov** — Coverage reporting
- **unittest.mock** — Mocking/patching
- **aioresponses** — Mock aiohttp responses

---

## CI/CD Integration

### GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `code-quality.yml` | Push to develop/testing/main | Syntax, quality, security checks |
| `enforce-merge-direction.yml` | Pull requests | Validate merge direction |

### Makefile Targets

```bash
make help              # Show all commands
make test              # Run all tests with coverage
make test-cov          # HTML coverage report
make lint              # Code quality (pylint, flake8)
make format            # Auto-format (black, isort)
make check-security    # Security scans (bandit)
```

---

## Manual Testing (Production)

### Pre-Deployment Checklist

- [ ] Backup existing configuration
- [ ] Dependencies updated (`pip install -r requirements.txt`)
- [ ] `.env` file configured with API_KEY
- [ ] Services restarted after update

### Failover Test Procedure

1. **Verify initial state:** both Pi-holes online, VIP on primary
2. **Trigger failover:** `systemctl stop pihole-FTL` on primary
3. **Verify:** VIP moves to secondary within 5s, DNS still resolves
4. **Restore:** `systemctl start pihole-FTL` on primary
5. **Verify:** VIP returns to primary, recovery notification sent

### Dashboard Verification

```bash
# API authentication
curl -s http://<monitor>:8080/api/status                    # -> 403
curl -s -H "X-API-Key: <key>" http://<monitor>:8080/api/status  # -> 200

# Core endpoints
curl -s -H "X-API-Key: <key>" http://<monitor>:8080/api/events?limit=10
curl -s -H "X-API-Key: <key>" http://<monitor>:8080/api/history?hours=1
curl -s -H "X-API-Key: <key>" http://<monitor>:8080/api/notification_settings
```

### Test Sign-Off Criteria (testing -> main)

- [ ] All automated tests pass
- [ ] Failover tested and working (< 5s)
- [ ] DNS disruption < 3s
- [ ] 7+ days stable in testing environment
- [ ] No critical bugs
- [ ] Browser compatibility verified
- [ ] Security audit passed

---

## Docker Integration Tests

### Setup

```bash
make docker-up              # Start mock environment (15 containers)
make docker-integration     # Run automated integration tests
make docker-status          # Manual status overview
make docker-down            # Cleanup
```

### Automated Tests (pytest)

Run via `make docker-integration`. Tests use the mock Pi-hole control API
to simulate failures and verify monitor responses.

| Test | Scenario | Validates |
|------|----------|-----------|
| `test_primary_offline_detected` | Primary FTL stops | Monitor detects offline |
| `test_primary_failure_logs_event` | Primary FTL stops | Event appears in timeline |
| `test_secondary_offline_detected` | Secondary FTL stops | Monitor detects offline |
| `test_secondary_failure_logs_event` | Secondary FTL stops | Event appears in timeline |
| `test_dhcp_disabled_on_primary_detected` | DHCP crash on primary | DHCP=false in status |
| `test_secondary_dhcp_state_reported` | Steady state | DHCP field exists in response |
| `test_primary_stats_nonzero` | Healthy state | queries, blocked, clients > 0 |
| `test_secondary_stats_nonzero` | Healthy state | queries > 0 |
| `test_primary_dhcp_enabled_as_master` | MASTER config | DHCP=true |
| `test_secondary_dhcp_disabled_as_backup` | BACKUP config | DHCP=false |
| `test_failure_and_recovery_events` | Failure + recovery | Both events logged |
| `test_leases_present` | Fake clients active | leases >= 3 |
| `test_full_recovery` | Offline → reset → check | All systems healthy |
| `test_history_has_entries` | After polling | History not empty |

### Visual Checklist (Manual)

After `make docker-up`, open `http://localhost:8080` in a browser.

#### V1. Dashboard Layout
- [ ] Both node cards visible and correctly labeled (Primary / Secondary)
- [ ] Stats show values > 0 (queries, blocked, clients)
- [ ] DHCP leases indicator shows a count
- [ ] Status graph loads and renders data points

#### V2. Failover Visual
- [ ] Run `make docker-failover`
- [ ] Primary card turns red / shows offline status within ~15s
- [ ] Events timeline shows failure event with timestamp
- [ ] Run `make docker-recover`
- [ ] Primary card returns to green / healthy
- [ ] Events timeline shows recovery event

#### V3. DHCP Indicator
- [ ] "DHCP Active" badge visible when DHCP is in use (green)
- [ ] Toggle primary DHCP off: `curl -X POST localhost:8001/mock/set-state -H 'Content-Type: application/json' -d '{"dhcp_enabled":false}'`
- [ ] After ~30s, indicator updates to reflect DHCP state change

#### V4. Dark Mode
- [ ] Toggle dark mode via UI switch
- [ ] All text remains readable
- [ ] Cards, graphs, and indicators adapt correctly

#### V5. Mobile Responsive
- [ ] Open dashboard at 375px width (phone)
- [ ] Cards stack vertically
- [ ] No horizontal scrolling required

---

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [tests/README.md](../../tests/README.md) — Test organization and execution guide
