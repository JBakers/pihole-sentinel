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
