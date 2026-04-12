#!/bin/bash
# DHCP service health check for keepalived
# This script checks if DHCP is enabled and the pihole-FTL service is responding

# Source the environment file for configuration
if [ -f /etc/keepalived/.env ]; then
    # Reject world-writable .env to prevent arbitrary code execution
    _perms=$(stat -c %a /etc/keepalived/.env 2>/dev/null)
    if [ -n "$_perms" ] && [ "${_perms: -1}" -ge 2 ] 2>/dev/null; then
        echo "ERROR: /etc/keepalived/.env is world-writable — refusing to source" >&2
        exit 1
    fi
    source /etc/keepalived/.env
fi

# If DHCP is not enabled in keepalived config, always return success
if [ "${DHCP_ENABLED}" != "true" ]; then
    exit 0
fi

# Check if pihole-FTL is running
if ! pgrep -x "pihole-FTL" > /dev/null; then
    exit 1
fi

# Check if DHCP is actually enabled in Pi-hole v6 config (TOML format)
# Uses pihole-FTL --config for reliable config reading
if ! pihole-FTL --config dhcp.active 2>/dev/null | grep -q "true"; then
    exit 1
fi

# All checks passed
exit 0
