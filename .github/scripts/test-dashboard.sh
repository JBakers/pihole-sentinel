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
