#!/bin/bash

# Define endpoints
TARGET="${PIHOLE_HOST:-127.0.0.1}"
DNS_PORT="${PIHOLE_DNS_PORT:-53}"
WEB_PORT="${PIHOLE_WEB_PORT:-80}"

# Check DNS Port (TCP)
if ! nc -z -w 2 "$TARGET" "$DNS_PORT"; then
    echo "DNS check failed on $TARGET:$DNS_PORT"
    exit 1
fi

# Check Web Interface
if ! curl -sf -m 2 "http://$TARGET:$WEB_PORT/admin/" > /dev/null; then
    # Fallback for mock environment (checking /mock/state)
    if ! curl -sf -m 2 "http://$TARGET:$WEB_PORT/mock/state" > /dev/null; then
        echo "Web Interface check failed on $TARGET:$WEB_PORT"
        exit 1
    fi
fi


exit 0
