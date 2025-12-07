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
