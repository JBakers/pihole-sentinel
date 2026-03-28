# Complete Testing & Development Workflow

**Version:** 0.12.0-beta.9  
**Last Updated:** 2025-12-07  
**Status:** ✅ Automated Testing Framework Ready

---

## 🎯 Executive Summary

Pi-hole Sentinel has a **comprehensive automated testing infrastructure** that validates code quality, security, and functionality before deployment. All components are integrated into a unified workflow.

**Quick Start:**
```bash
# Run all automated checks locally
make test                    # Full test suite with coverage
make lint                    # Code quality checks
make format                  # Auto-format code
./.github/scripts/run-all-tests.sh  # All automated tests
```

---

## 📋 Testing Architecture

### Test Levels (Pyramid)

```
                    ▲
                   /        \
                  / Manual  /
                 / Tests   /  (Integration, Failover, Load)
                ▲          ▼
               /              \
              / Integration    \  (API endpoints, Async ops, DB)
             / Tests          /
            ▲                  ▼
           /                      \
          / Unit Tests            \  (Validation, Models, Handlers)
         / (86 tests, 1423 LOC)   /
        ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▼
        Automated & Fast (Key for CI/CD)
```

### Test Layers

| Layer | Tests | Speed | Coverage |
|-------|-------|-------|----------|
| **Unit** | 86 existing + 40 new | <1s | 50-70% |
| **Integration** | 20+ (API endpoints, DB, Async) | 5-10s | 80%+ target |
| **Functional** | Manual: failover, DHCP, DNS | Variable | Critical paths |
| **Security** | API key, CORS, rate limiting | 1-2s | Custom scenarios |
| **Performance** | Load, timeout, retry scenarios | 10-30s | Key metrics |

---

## ⚙️ Available Test Scripts

### Automated Tests (Ready to Use)

Located in `.github/scripts/`

#### 1. **run-all-tests.sh** - Master Runner
```bash
./.github/scripts/run-all-tests.sh
```
Runs: syntax checks → quality checks → security scans  
**Output:** Pass/fail summary  
**Time:** ~10-30 seconds

#### 2. **run-syntax-checks.sh** - Python & Bash Syntax
```bash
./.github/scripts/run-syntax-checks.sh
```
Validates:
- Python files (monitor.py, setup.py)
- Bash scripts (keepalived, sync-pihole-config)

**Output:** Syntax errors or ✓ OK

#### 3. **run-quality-checks.sh** - Code Quality
```bash
./.github/scripts/run-quality-checks.sh
```
Checks:
- Print statements in Python (except setup.py)
- CRLF line endings in bash scripts
- Required files exist (VERSION, CHANGELOG.md, LICENSE)
- Version file consistency

**Output:** Quality issues with file/line references

#### 4. **run-security-scans.sh** - Security Audit
```bash
./.github/scripts/run-security-scans.sh
```
Scans for:
- Hardcoded secrets / API keys
- Security vulnerabilities (bandit)
- Weak password patterns
- File permission issues

**Output:** Security findings with severity levels

#### 5. **test-failover.sh** - Failover Simulation
```bash
./.github/scripts/test-failover.sh <VIP> <primary_ip> <secondary_ip>

# Example:
./.github/scripts/test-failover.sh 192.168.1.100 192.168.1.10 192.168.1.11
```
Tests:
- VIP location detection
- Master/backup status
- Failover trigger and response
- DNS / DHCP failure handling

**Output:** Failover events with timing

#### 6. **test-dashboard.sh** - API Validation
```bash
./.github/scripts/test-dashboard.sh <monitor_ip> <api_key>

# Example:
./.github/scripts/test-dashboard.sh 192.168.1.5 "your-api-key"
```
Tests:
- API endpoints (version, status, events, notifications)
- Authentication (API key validation)
- Response format validation
- Error handling

**Output:** Endpoint test results

#### 7. **generate-test-summary.sh** - Report Generation
```bash
./.github/scripts/generate-test-summary.sh <report_file>

# Example:
./.github/scripts/generate-test-summary.sh .github/test-reports/TEST_REPORT_$(date +%Y%m%d).md
```
Generates: Markdown test report with results

#### 8. **nightly-tests.sh** - Automated Nightly Runs
```bash
# Add to crontab:
0 2 * * * /path/to/.github/scripts/nightly-tests.sh >> /var/log/nightly-tests.log 2>&1
```
Runs all tests automatically each night

---

## 🚀 Recommended Testing Workflow

### For Local Development

**Before pushing:**
```bash
# 1. Format code
make format

# 2. Run all checks locally
make test              # Unit tests + coverage
./.github/scripts/run-all-tests.sh  # Full quality suite

# 3. If all pass → ready to commit
git add -A
git commit -m "feat: your change"
git push
```

### For Testing Branch

**Before merging develop → testing:**
```bash
git checkout testing

# 1. Run automated tests
./.github/scripts/run-all-tests.sh

# 2. If deployed, run failover tests
./.github/scripts/test-failover.sh $VIP $PRIMARY $SECONDARY

# 3. If dashboard running, validate API
./.github/scripts/test-dashboard.sh $MONITOR_IP $API_KEY

# 4. Generate test report
./.github/scripts/generate-test-summary.sh .github/test-reports/TEST_REPORT_$(date +%Y%m%d).md

# 5. Review report and commit
git add .github/test-reports/
git commit -m "test: add test report for $(date +%Y-%m-%d)"
```

### For Main Branch

**Before merging testing → main:**
```bash
# 1. Verify all testing branch tests passed
cat .github/test-reports/TEST_REPORT_latest.md | grep -E "(PASS|FAIL)"

# 2. Confirm 7+ days stable operation in testing

# 3. Manual QA sign-off:
#    - Failover scenarios tested
#    - DHCP failover validated
#    - Long-running stability confirmed
#    - No critical bugs

# 4. Create release tag
git tag -a v0.12.0 -m "Release version 0.12.0"
git push origin v0.12.0

# 5. Merge to main
git checkout main
git merge testing
git push origin main
```

---

## 📊 Test Coverage Overview

### Current Coverage (Known Tested Areas)

✅ **Unit Tests (86 cases):**
- Input validation (IP, subnet, interface, port, username)
- Injection attack prevention
- DHCP parsing and state detection
- VIP/MAC detection logic
- Pi-hole API authentication

✅ **Integration Tests (Partial):**
- API handlers (auth, DHCP, stats)
- Connection management
- HTTP session handling

⚠️ **Gaps Identified (NEW):**
- Error handling (new 6 exception classes)
- Async operations (monitor loop, notifications)
- API endpoint responses (new Pydantic models)
- Database operations
- Configuration edge cases
- Security hardening

### Coverage Targets

| Module | Current | Target | Plan |
|--------|---------|--------|------|
| `dashboard/monitor.py` | ~40% | 85% | +45% (Tier 2) |
| `setup.py` | ~60% | 90% | +30% (Tier 2) |
| Overall | ~50% | 95% | +45% (34 hours) |

---

## 🧪 CI/CD Integration

### GitHub Actions Workflows

Located in `.github/workflows/`

#### 1. **code-quality.yml** (On every push)
```yaml
Jobs:
  - python-checks (Black, Flake8, Pylint, Syntax)
  - shell-checks (ShellCheck, Bash syntax)
  - markdown-checks (Markdownlint)
  - security-checks (Bandit, Safety)
  - file-checks (Secrets, CRLF, Required files)
```

**Triggers:** Push to develop/testing/main, Pull requests  
**Status:** ✅ Automated

#### 2. **enforce-merge-direction.yml** (On pull requests)
```yaml
Job:
  - Validates merge direction (features→develop→testing→main)
  - Blocks unauthorized reverse merges
```

**Triggers:** Pull requests  
**Status:** ✅ Automated

#### 3. **test-automation.yml** (Proposed - On testing branch)
```yaml
Jobs:
  - run-all-tests.sh
  - test-failover.sh (if deployed)
  - test-dashboard.sh (if running)
  - generate-test-summary.sh
  - upload-coverage-to-codecov
```

**Triggers:** Merge to testing  
**Status:** 🔧 Ready to implement

---

## 🐳 Docker Testing Environment (Proposed)

### Docker Compose Setup

**File:** `docker-compose.test.yml`

```yaml
version: '3.8'

services:
  # Test Pi-hole instances
  pihole-primary:
    image: pihole/pihole:latest
    environment:
      - WEBPASSWORD=testpass
      - TZ=UTC
    ports:
      - "8081:80"
      - "53:53/udp"
      - "53:53/tcp"
    networks:
      - test-net

  pihole-secondary:
    image: pihole/pihole:latest
    environment:
      - WEBPASSWORD=testpass
      - TZ=UTC
    ports:
      - "8082:80"
      - "153:53/udp"
      - "153:53/tcp"
    networks:
      - test-net

  # Pi-hole Sentinel Monitor
  sentinel-monitor:
    build: .
    environment:
      - PRIMARY_IP=pihole-primary
      - PRIMARY_PASSWORD=testpass
      - SECONDARY_IP=pihole-secondary
      - SECONDARY_PASSWORD=testpass
      - VIP_ADDRESS=172.20.0.100
      - API_KEY=test-api-key
      - CHECK_INTERVAL=5
    ports:
      - "8080:8080"
    depends_on:
      - pihole-primary
      - pihole-secondary
    networks:
      - test-net

networks:
  test-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

**Usage:**
```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run tests against Docker environment
./.github/scripts/test-dashboard.sh 172.20.0.3 test-api-key

# Stop and cleanup
docker-compose -f docker-compose.test.yml down
```

---

## 📋 Integration with Makefile

Current Makefile targets:

```bash
make help              # Show all commands
make install           # Install production deps
make install-dev       # Install dev deps
make test              # Run all tests with coverage
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-cov          # HTML coverage report
make test-fast         # Quick tests (no coverage)
make lint              # Code quality (pylint, flake8)
make format            # Auto-format (black, isort)
make check-security    # Security scans (bandit, safety)
make clean             # Remove generated files
```

---

## ✅ Test Execution Checklist

### Before Each Commit

- [ ] Run `make format` to auto-format code
- [ ] Run `make test` to verify tests pass
- [ ] Run `make lint` to check code quality
- [ ] Run `./.github/scripts/run-all-tests.sh` for full validation
- [ ] Review changes before committing
- [ ] Commit message follows conventional commits (feat:, fix:, etc.)

### Before Pushing to develop

- [ ] All local tests pass
- [ ] Documentation updated (README, API docs, etc.)
- [ ] VERSION file updated
- [ ] CHANGELOG.md updated
- [ ] No print() statements left in code

### Before Merging develop → testing

- [ ] GitHub Actions CI/CD passes (all checks green)
- [ ] Manual testing completed (if applicable)
- [ ] Test report generated and reviewed
- [ ] No merge conflicts
- [ ] Semantic version bumped correctly

### Before Merging testing → main

- [ ] At least 7 days stable in testing
- [ ] All failover scenarios tested and working
- [ ] Browser compatibility verified
- [ ] Performance benchmarks met
- [ ] Security audit passed
- [ ] Product owner sign-off obtained

---

## 🔍 Debugging Test Failures

### Python Test Issues

```bash
# Run specific test with verbose output
pytest tests/test_error_handling.py::TestExceptionHierarchy::test_pihole_sentinel_exception_base -vv

# Run with print statements visible
pytest tests/test_error_handling.py -s

# Run with detailed failure info
pytest tests/test_error_handling.py -vv --tb=long

# Run with debugger
pytest tests/test_error_handling.py --pdb
```

### Bash Script Issues

```bash
# Enable debugging output
bash -x ./.github/scripts/run-all-tests.sh

# Test individual scripts
bash -n /path/to/script.sh  # Syntax check only

# Run with detailed output
set -x ; bash script.sh ; set +x
```

### CI/CD Issues

```bash
# View GitHub Actions logs
# Navigate to: https://github.com/JBakers/pihole-sentinel/actions
# Click failing workflow → View logs

# Re-run failed workflow
# In GitHub: Click "Re-run all jobs" button
```

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | AI assistant guidelines + testing section |
| `docs/development/testing.md` | Manual testing procedures for end users |
| `docs/development/TEST_COVERAGE_PLAN.md` | Coverage goals and improvement roadmap |
| `tests/README.md` | Test organization and execution guide |
| `pytest.ini` | Pytest configuration (coverage thresholds) |
| `Makefile` | Common development commands |

---

## 🎯 Success Metrics

### Code Quality
- ✅ All syntax checks pass
- ✅ No print() statements (except setup.py)
- ✅ CRLF line endings corrected
- ✅ Required files present

### Test Coverage
- ✅ 50%+ current coverage
- ✅ 95%+ target coverage (Tier 2 goal)
- ✅ All critical paths tested
- ✅ No untested exceptions

### Functionality
- ✅ Failover triggers correctly
- ✅ VIP moves between nodes
- ✅ DNS/DHCP service survives failover
- ✅ Monitoring dashboard responsive

### Security
- ✅ No hardcoded secrets
- ✅ API key authentication working
- ✅ Rate limiting enforced
- ✅ CORS policy correct

### Performance
- ✅ Failover < 5 seconds
- ✅ DNS disruption < 3 seconds
- ✅ API response < 500ms
- ✅ No memory leaks (7+ days)

---

## 🔗 Related Documents

- **[CLAUDE.md](CLAUDE.md)** - Testing guidelines for AI assistants
- **[docs/development/testing.md](docs/development/testing.md)** - User manual testing guide
- **[docs/development/TEST_COVERAGE_PLAN.md](docs/development/TEST_COVERAGE_PLAN.md)** - Coverage roadmap
- **[docs/api/README.md](docs/api/README.md)** - API reference with examples
- **[pytest.ini](pytest.ini)** - Test configuration
- **[Makefile](Makefile)** - Development commands
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

---

## 📞 Next Steps

1. **Implement Docker Compose setup** for isolated testing
2. **Expand test coverage** to 95%+ (Tier 2 focus)
3. **Add CI/CD integration test job** to GitHub Actions
4. **Setup nightly automated tests** via cron
5. **Generate automated coverage reports** with codecov integration

