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
