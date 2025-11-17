#!/bin/bash
# Run all automated tests
# Usage: ./run-all-tests.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Running All Automated Tests ==="
echo ""

# Run syntax checks
echo "1/3 Running syntax checks..."
"$SCRIPT_DIR/run-syntax-checks.sh"
echo ""

# Run quality checks
echo "2/3 Running quality checks..."
"$SCRIPT_DIR/run-quality-checks.sh"
echo ""

# Run security scans
echo "3/3 Running security scans..."
"$SCRIPT_DIR/run-security-scans.sh"
echo ""

echo "=== All Automated Tests Complete ==="
echo ""
echo "Note: Failover and dashboard tests require deployed environment."
echo "Run manually with:"
echo "  - ./test-failover.sh <VIP> <primary_ip> <secondary_ip>"
echo "  - ./test-dashboard.sh <monitor_ip> <api_key>"
