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
