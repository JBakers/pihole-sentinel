#!/bin/bash
# DHCP service health check for keepalived
# This script checks if DHCP is enabled and the dnsmasq service is responding to DHCP requests

# Source the environment file for configuration
if [ -f /etc/keepalived/.env ]; then
    source /etc/keepalived/.env
fi

# If DHCP is not enabled, always return success (no need to check)
if [ "${DHCP_ENABLED}" != "true" ]; then
    exit 0
fi

# Check if dnsmasq is running
if ! pgrep -x "pihole-FTL" > /dev/null; then
    exit 1
fi

# Check if DHCP is actually enabled in Pi-hole config
if ! grep -q "^dhcp-range=" /etc/dnsmasq.d/02-pihole-dhcp.conf 2>/dev/null; then
    exit 1
fi

# All checks passed
exit 0
