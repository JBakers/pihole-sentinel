# Test Automation Guide

**Purpose:** This guide explains how to use the testing infrastructure and automate test documentation for the `testing` branch.

---

## Quick Start

### 1. Starting a New Test Cycle

```bash
# Switch to testing branch
git checkout testing

# Pull latest changes from develop
git merge develop

# Create test documentation from template
cp .github/TEST_DOCUMENTATION_TEMPLATE.md .github/test-reports/TEST_REPORT_$(date +%Y%m%d).md

# Edit the report with your environment details
nano .github/test-reports/TEST_REPORT_$(date +%Y%m%d).md
```

### 2. Running Automated Checks

```bash
# Run syntax checks
bash .github/scripts/run-syntax-checks.sh

# Run code quality checks
bash .github/scripts/run-quality-checks.sh

# Run security scans
bash .github/scripts/run-security-scans.sh
```

### 3. Documenting Test Results

As you complete each test, update the test report markdown file with:
- ✅ PASS - Test passed successfully
- ❌ FAIL - Test failed (document issues)
- ⏭️ SKIP - Test skipped (document reason)

### 4. Generating Test Summary

```bash
# Generate summary from test report
bash .github/scripts/generate-test-summary.sh .github/test-reports/TEST_REPORT_$(date +%Y%m%d).md
```

---

## Test Workflow

### Daily Testing Routine

```
┌──────────────────────────────────────────┐
│ 1. Merge latest from develop            │
│    git merge develop                     │
└─────────────┬────────────────────────────┘
              │
┌─────────────▼────────────────────────────┐
│ 2. Run automated tests                   │
│    - Syntax checks                       │
│    - Code quality                        │
│    - Security scans                      │
└─────────────┬────────────────────────────┘
              │
┌─────────────▼────────────────────────────┐
│ 3. Run manual tests                      │
│    - Deployment tests                    │
│    - Failover tests                      │
│    - Dashboard tests                     │
└─────────────┬────────────────────────────┘
              │
┌─────────────▼────────────────────────────┐
│ 4. Document results                      │
│    - Update test report                  │
│    - Add screenshots                     │
│    - Log issues                          │
└─────────────┬────────────────────────────┘
              │
┌─────────────▼────────────────────────────┐
│ 5. Daily review                          │
│    - Check progress                      │
│    - Update TODO list                    │
│    - Plan next tests                     │
└──────────────────────────────────────────┘
```

### Weekly Testing Routine

```
┌──────────────────────────────────────────┐
│ 1. Review week's test results           │
│    - Pass/fail rate                      │
│    - Bug trends                          │
│    - Performance metrics                 │
└─────────────┬────────────────────────────┘
              │
┌─────────────▼────────────────────────────┐
│ 2. Update TESTING_TODO.md                │
│    - Mark completed tests                │
│    - Add new tests                       │
│    - Prioritize failures                 │
└─────────────┬────────────────────────────┘
              │
┌─────────────▼────────────────────────────┐
│ 3. Bug triage                            │
│    - Categorize bugs                     │
│    - Assign priorities                   │
│    - Create GitHub issues                │
└─────────────┬────────────────────────────┘
              │
┌─────────────▼────────────────────────────┐
│ 4. Long-running tests                    │
│    - 7-day stability test                │
│    - Database growth analysis            │
│    - Memory leak detection               │
└──────────────────────────────────────────┘
```

---

## Automated Test Scripts

### Syntax Checks

**File:** `.github/scripts/run-syntax-checks.sh`

```bash
#!/bin/bash
set -e

echo "=== Running Syntax Checks ==="

# Python syntax check
echo "Checking Python syntax..."
python3 -m py_compile dashboard/monitor.py
python3 -m py_compile setup.py
echo "✓ Python syntax OK"

# Bash syntax check
echo "Checking Bash syntax..."
for script in keepalived/scripts/*.sh sync-pihole-config.sh; do
    bash -n "$script"
done
echo "✓ Bash syntax OK"

echo "=== All Syntax Checks Passed ==="
```

### Quality Checks

**File:** `.github/scripts/run-quality-checks.sh`

```bash
#!/bin/bash
set -e

echo "=== Running Code Quality Checks ==="

# Check for print statements in monitor.py
echo "Checking for print() statements..."
if grep -n "print(" dashboard/monitor.py; then
    echo "✗ Found print() statements in monitor.py (should use logger)"
    exit 1
fi
echo "✓ No print() statements in monitor.py"

# Check CRLF line endings
echo "Checking line endings..."
if find . -name "*.sh" -exec file {} \; | grep -q CRLF; then
    echo "✗ Found CRLF line endings in shell scripts"
    exit 1
fi
echo "✓ Line endings OK"

# Check required files
echo "Checking required files..."
for file in README.md CHANGELOG.md LICENSE VERSION CLAUDE.md; do
    test -f "$file" || (echo "✗ Missing $file" && exit 1)
done
echo "✓ Required files present"

echo "=== All Quality Checks Passed ==="
```

### Security Scans

**File:** `.github/scripts/run-security-scans.sh`

```bash
#!/bin/bash
set -e

echo "=== Running Security Scans ==="

# Check for hardcoded secrets
echo "Checking for hardcoded secrets..."
if grep -r -i "password.*=.*['\"].*['\"]" --include="*.py" --include="*.sh" . | grep -v -E "(.env|.example|template)"; then
    echo "⚠ Warning: Potential hardcoded password found"
fi

# Check file permissions (if deployed)
if [ -f "/etc/keepalived/.env" ]; then
    echo "Checking file permissions..."
    perm=$(stat -c %a /etc/keepalived/.env)
    if [ "$perm" != "600" ]; then
        echo "✗ /etc/keepalived/.env has incorrect permissions: $perm (should be 600)"
        exit 1
    fi
    echo "✓ File permissions OK"
fi

echo "=== Security Scans Complete ==="
```

### Test Summary Generator

**File:** `.github/scripts/generate-test-summary.sh`

```bash
#!/bin/bash
# Usage: ./generate-test-summary.sh TEST_REPORT_20251116.md

REPORT_FILE="$1"

if [ ! -f "$REPORT_FILE" ]; then
    echo "Error: Report file not found: $REPORT_FILE"
    exit 1
fi

echo "=== Test Summary ==="
echo ""

# Count PASS/FAIL/SKIP
PASS=$(grep -c "\[ x \] PASS" "$REPORT_FILE" || echo "0")
FAIL=$(grep -c "\[ x \] FAIL" "$REPORT_FILE" || echo "0")
SKIP=$(grep -c "\[ x \] SKIP" "$REPORT_FILE" || echo "0")
TOTAL=$((PASS + FAIL + SKIP))

# Calculate pass rate
if [ "$TOTAL" -gt 0 ]; then
    PASS_RATE=$((PASS * 100 / TOTAL))
else
    PASS_RATE=0
fi

echo "Total Tests: $TOTAL"
echo "Passed:      $PASS"
echo "Failed:      $FAIL"
echo "Skipped:     $SKIP"
echo "Pass Rate:   $PASS_RATE%"
echo ""

# Check if ready for merge
if [ "$FAIL" -eq 0 ] && [ "$PASS_RATE" -ge 95 ]; then
    echo "✓ Ready for merge to main"
else
    echo "✗ Not ready for merge (fix failures or increase pass rate)"
fi
```

---

## Test Execution Templates

### Failover Test Script

**File:** `.github/scripts/test-failover.sh`

```bash
#!/bin/bash
# Automated failover test
# Usage: ./test-failover.sh <VIP> <primary_ip> <secondary_ip>

VIP="$1"
PRIMARY="$2"
SECONDARY="$3"

echo "=== Starting Failover Test ==="
echo "VIP: $VIP"
echo "Primary: $PRIMARY"
echo "Secondary: $SECONDARY"

# Pre-test: Check VIP location
echo -n "Checking VIP location... "
before_vip=$(ssh root@$PRIMARY "ip addr show | grep -c $VIP" || echo "0")
if [ "$before_vip" = "1" ]; then
    echo "VIP on Primary ✓"
else
    echo "VIP NOT on Primary ✗"
    exit 1
fi

# Test DNS before failover
echo -n "Testing DNS before failover... "
if dig @$VIP example.com +short | grep -q .; then
    echo "OK ✓"
else
    echo "FAIL ✗"
    exit 1
fi

# Trigger failover
echo "Triggering failover (stopping pihole-FTL on primary)..."
START_TIME=$(date +%s)
ssh root@$PRIMARY "systemctl stop pihole-FTL"

# Wait for VIP to move
echo -n "Waiting for VIP to move... "
for i in {1..15}; do
    sleep 1
    after_vip=$(ssh root@$SECONDARY "ip addr show | grep -c $VIP" || echo "0")
    if [ "$after_vip" = "1" ]; then
        END_TIME=$(date +%s)
        FAILOVER_TIME=$((END_TIME - START_TIME))
        echo "VIP moved in ${FAILOVER_TIME}s ✓"
        break
    fi
done

if [ "$after_vip" != "1" ]; then
    echo "TIMEOUT ✗"
    ssh root@$PRIMARY "systemctl start pihole-FTL"
    exit 1
fi

# Test DNS after failover
echo -n "Testing DNS after failover... "
if dig @$VIP example.com +short | grep -q .; then
    echo "OK ✓"
else
    echo "FAIL ✗"
    ssh root@$PRIMARY "systemctl start pihole-FTL"
    exit 1
fi

# Restore primary
echo "Restoring primary..."
ssh root@$PRIMARY "systemctl start pihole-FTL"
sleep 5

echo "=== Failover Test Complete ==="
echo "Failover Time: ${FAILOVER_TIME}s"
if [ "$FAILOVER_TIME" -lt 5 ]; then
    echo "Result: PASS ✓"
    exit 0
else
    echo "Result: FAIL (> 5s) ✗"
    exit 1
fi
```

### Dashboard Test Script

**File:** `.github/scripts/test-dashboard.sh`

```bash
#!/bin/bash
# Automated dashboard test
# Usage: ./test-dashboard.sh <monitor_ip> <api_key>

MONITOR_IP="$1"
API_KEY="$2"

echo "=== Starting Dashboard Test ==="

# Test status endpoint
echo -n "Testing /api/status... "
STATUS=$(curl -s -H "X-API-Key: $API_KEY" "http://$MONITOR_IP:8080/api/status")
if [ $? -eq 0 ] && echo "$STATUS" | jq -e '.timestamp' > /dev/null 2>&1; then
    echo "OK ✓"
else
    echo "FAIL ✗"
    exit 1
fi

# Test history endpoint
echo -n "Testing /api/history... "
HISTORY=$(curl -s -H "X-API-Key: $API_KEY" "http://$MONITOR_IP:8080/api/history?hours=1")
if [ $? -eq 0 ] && echo "$HISTORY" | jq -e 'type == "array"' > /dev/null 2>&1; then
    echo "OK ✓"
else
    echo "FAIL ✗"
    exit 1
fi

# Test events endpoint
echo -n "Testing /api/events... "
EVENTS=$(curl -s -H "X-API-Key: $API_KEY" "http://$MONITOR_IP:8080/api/events?limit=10")
if [ $? -eq 0 ] && echo "$EVENTS" | jq -e 'type == "array"' > /dev/null 2>&1; then
    echo "OK ✓"
else
    echo "FAIL ✗"
    exit 1
fi

# Test dashboard HTML
echo -n "Testing dashboard HTML... "
if curl -s "http://$MONITOR_IP:8080/" | grep -q "Pi-hole Sentinel"; then
    echo "OK ✓"
else
    echo "FAIL ✗"
    exit 1
fi

echo "=== Dashboard Test Complete: PASS ✓ ==="
exit 0
```

---

## Continuous Testing Strategy

### Nightly Automated Tests

**Schedule:** Every night at 2 AM

```bash
#!/bin/bash
# Nightly automated test run
# Add to crontab: 0 2 * * * /path/to/nightly-tests.sh

LOG_DIR="/var/log/pihole-sentinel-tests"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/nightly-$(date +%Y%m%d).log"

{
    echo "=== Nightly Test Run: $(date) ==="

    # Syntax checks
    .github/scripts/run-syntax-checks.sh

    # Quality checks
    .github/scripts/run-quality-checks.sh

    # Security scans
    .github/scripts/run-security-scans.sh

    # Failover test
    .github/scripts/test-failover.sh 10.10.100.2 10.10.100.10 10.10.100.20

    # Dashboard test
    .github/scripts/test-dashboard.sh 10.10.100.30 "$API_KEY"

    echo "=== Test Run Complete ==="
} 2>&1 | tee -a "$LOG_FILE"

# Send notification on failure
if grep -q "FAIL" "$LOG_FILE"; then
    # Send alert (configure notification service)
    echo "Nightly tests failed! Check $LOG_FILE" | mail -s "Pi-hole Sentinel Test Failure" admin@example.com
fi
```

### Weekly Stress Tests

**Schedule:** Every Sunday at 3 AM

```bash
#!/bin/bash
# Weekly stress test
# Add to crontab: 0 3 * * 0 /path/to/weekly-stress-test.sh

LOG_FILE="/var/log/pihole-sentinel-tests/weekly-$(date +%Y%m%d).log"

{
    echo "=== Weekly Stress Test: $(date) ==="

    # Load test (10 minutes, 1000 queries/sec)
    echo "Running DNS load test..."
    dnsperf -d queries.txt -s 10.10.100.2 -l 600 -Q 1000

    # Database size check
    echo "Checking database size..."
    du -h /opt/pihole-monitor/monitor.db

    # Memory usage check
    echo "Checking memory usage..."
    free -h
    ps aux | grep -E "(pihole-monitor|keepalived)" | grep -v grep

    echo "=== Stress Test Complete ==="
} 2>&1 | tee -a "$LOG_FILE"
```

---

## Test Data Management

### Test Environment Snapshots

```bash
# Create snapshot before testing
virsh snapshot-create-as pihole-primary "Before testing $(date +%Y%m%d)" --disk-only

# Restore snapshot if tests fail
virsh snapshot-revert pihole-primary "Before testing 20251116"
```

### Test Data Cleanup

```bash
# Clean old test reports (keep last 30 days)
find .github/test-reports/ -name "TEST_REPORT_*.md" -mtime +30 -delete

# Clean old logs
find /var/log/pihole-sentinel-tests/ -name "*.log" -mtime +60 -delete
```

---

## Integration with CI/CD

### GitHub Actions Integration

Add to `.github/workflows/testing-branch.yml`:

```yaml
name: Testing Branch Checks

on:
  push:
    branches: [ testing ]
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM

jobs:
  automated-tests:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run syntax checks
        run: bash .github/scripts/run-syntax-checks.sh

      - name: Run quality checks
        run: bash .github/scripts/run-quality-checks.sh

      - name: Run security scans
        run: bash .github/scripts/run-security-scans.sh

      - name: Generate test summary
        if: always()
        run: |
          echo "## Test Summary" >> $GITHUB_STEP_SUMMARY
          bash .github/scripts/generate-test-summary.sh .github/test-reports/TEST_REPORT_latest.md >> $GITHUB_STEP_SUMMARY
```

---

## Test Result Interpretation

### Pass Criteria

✅ **PASS:** Test met all requirements
- No errors or unexpected behavior
- Performance within thresholds
- Documentation matches implementation

### Fail Criteria

❌ **FAIL:** Test did not meet requirements
- Errors or exceptions occurred
- Performance below thresholds
- Functionality broken or incorrect

### Skip Criteria

⏭️ **SKIP:** Test not applicable or blocked
- Feature not implemented yet
- Dependencies missing
- Platform-specific (not applicable)

---

## Reporting Bugs

### Bug Report Template

```markdown
**Title:** [Short description]

**Priority:** Critical / High / Medium / Low

**Environment:**
- Branch: testing
- Commit: [hash]
- OS: [e.g., Debian 12]

**Steps to Reproduce:**
1. ...
2. ...
3. ...

**Expected Behavior:**
[What should happen]

**Actual Behavior:**
[What actually happened]

**Logs:**
```
[Paste relevant logs]
```

**Screenshots:**
[Attach screenshots if applicable]

**Additional Context:**
[Any other relevant information]
```

### Bug Triage Process

1. **Categorize:** Critical / High / Medium / Low
2. **Assign:** Assign to developer or maintainer
3. **Track:** Create GitHub issue
4. **Fix:** Fix in `develop` branch
5. **Verify:** Merge to `testing` and re-test
6. **Close:** Mark as resolved when verified

---

## Best Practices

### DO

✅ Test on clean environments (VMs/containers)
✅ Document every test execution
✅ Take screenshots for visual tests
✅ Save log files for debugging
✅ Run tests multiple times for reliability
✅ Test all platforms and browsers
✅ Update TESTING_TODO.md regularly
✅ Communicate test results to team

### DON'T

❌ Skip tests due to time pressure
❌ Test on production systems
❌ Ignore failed tests
❌ Modify code on testing branch (use develop)
❌ Merge to main without sign-off
❌ Delete test reports (archive instead)
❌ Run destructive tests without backups

---

## Troubleshooting

### Common Issues

**Issue:** Tests fail intermittently
**Solution:** Run tests multiple times, check for race conditions

**Issue:** Environment differs from production
**Solution:** Use identical VMs/containers, document differences

**Issue:** Tests take too long
**Solution:** Parallelize tests, optimize test scripts

**Issue:** Lost test data
**Solution:** Regular backups, commit test reports to git

---

## Resources

### Documentation

- [TESTING_TODO.md](.github/TESTING_TODO.md) - Test checklist
- [TEST_DOCUMENTATION_TEMPLATE.md](.github/TEST_DOCUMENTATION_TEMPLATE.md) - Report template
- [TESTING-GUIDE.md](../TESTING-GUIDE.md) - User testing guide

### Tools

- `dnsperf` - DNS load testing
- `curl` - API testing
- `jq` - JSON parsing
- `shellcheck` - Shell script linting
- `pylint` - Python linting

### External Resources

- [Testing Best Practices](https://docs.github.com/en/actions/automating-builds-and-tests)
- [Bash Testing Framework](https://github.com/bats-core/bats-core)
- [Python Testing](https://docs.pytest.org/)

---

**Last Updated:** 2025-11-16
**Maintainer:** JBakers
**Questions?** Open an issue on GitHub
