#!/bin/bash
set -e

if [ -z "$VIP_IP" ]; then
    echo "Error: VIP_IP is required"
    exit 1
fi

# Map NODE_ROLE to keepalived state
if [ "$NODE_ROLE" = "master" ] || [ "$NODE_ROLE" = "primary" ]; then
    export KEEPALIVED_STATE="MASTER"
fi

echo "Generating keepalived config..."
echo "  State:    $KEEPALIVED_STATE"
echo "  Priority: $KEEPALIVED_PRIORITY"
echo "  VIP:      $VIP_IP"

envsubst < /etc/keepalived/keepalived.conf.tpl > /etc/keepalived/keepalived.conf

exec keepalived --dont-fork --log-console --log-detail
