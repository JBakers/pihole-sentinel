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
