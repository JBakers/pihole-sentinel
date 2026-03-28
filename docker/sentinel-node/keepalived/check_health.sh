#!/bin/bash
# Health check for keepalived VRRP script tracking
# Checks that the paired Pi-hole is healthy (DNS + Web)

TARGET="${PIHOLE_HOST:-127.0.0.1}"
DNS_PORT="${PIHOLE_DNS_PORT:-53}"
WEB_PORT="${PIHOLE_WEB_PORT:-80}"

# Check DNS (TCP connect)
if ! nc -z -w 2 "$TARGET" "$DNS_PORT" 2>/dev/null; then
    exit 1
fi

# Check Web (Pi-hole API or mock)
if ! curl -sf -m 2 "http://$TARGET:$WEB_PORT/api/version" > /dev/null 2>&1; then
    if ! curl -sf -m 2 "http://$TARGET:$WEB_PORT/mock/state" > /dev/null 2>&1; then
        exit 1
    fi
fi

exit 0
