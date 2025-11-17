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

    # Failover test (configure your IPs)
    # .github/scripts/test-failover.sh 10.10.100.2 10.10.100.10 10.10.100.20

    # Dashboard test (configure your IP and API key)
    # .github/scripts/test-dashboard.sh 10.10.100.30 "$API_KEY"

    echo "=== Test Run Complete ==="
} 2>&1 | tee -a "$LOG_FILE"

# Send notification on failure
if grep -q "FAIL" "$LOG_FILE"; then
    # Send alert (configure notification service)
    echo "Nightly tests failed! Check $LOG_FILE" | mail -s "Pi-hole Sentinel Test Failure" admin@example.com
fi
