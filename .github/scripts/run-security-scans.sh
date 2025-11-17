#!/bin/bash
set -e

echo "=== Running Security Scans ==="

# Check for hardcoded secrets
echo "Checking for hardcoded secrets..."
# Look for actual hardcoded passwords (string literals), excluding safe patterns
RESULT=$(grep -r -i "password.*=.*['\"][a-zA-Z0-9_!@#\$%^&*-]\+['\"]" --include="*.py" --include="*.sh" . \
    | grep -v -E "(.env|.example|template)" \
    | grep -v "getpass(" \
    | grep -v "\.get(" \
    | grep -v "def .*password.*=" \
    | grep -v "password=None" \
    | grep -v -F "PRIMARY_PASSWORD={" \
    | grep -v -F "SECONDARY_PASSWORD={" \
    || true)

if [ -n "$RESULT" ]; then
    echo "$RESULT"
    echo "⚠ Warning: Potential hardcoded password found"
else
    echo "✓ No hardcoded secrets found"
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
