#!/bin/bash
set -e

# Validate required variables
if [ -z "$VIP_IP" ]; then
    echo "Error: VIP_IP environment variable is required"
    exit 1
fi

echo "Generating keepalived configuration..."
echo "  State: $KEEPALIVED_STATE"
echo "  Priority: $KEEPALIVED_PRIORITY"
echo "  Interface: $KEEPALIVED_INTERFACE"
echo "  VIP: $VIP_IP"

# Replace variables in template
envsubst < /etc/keepalived/keepalived.conf.tpl > /etc/keepalived/keepalived.conf

# Verify config
echo "Verifying configuration..."
# cat /etc/keepalived/keepalived.conf

echo "Starting Keepalived..."
exec keepalived --dont-fork --log-console --log-detail --dump-conf
