#!/bin/bash

CONFIG_FILE="/etc/pihole/pihole.toml"

# 1. Check if the FTL service is active at all
if ! systemctl is-active --quiet pihole-FTL; then
    exit 1
fi

# Add a short pause to give FTL time to fully initialize
sleep 1

# 2. Check if DNS functionality responds locally
if ! timeout 2 dig @127.0.0.1 pi.hole +short &>/dev/null; then
    exit 1
fi

# 3. Smart DHCP check: only check DHCP port if service is configured as active IN THE DHCP SECTION
if sed -n '/^\[dhcp\]/,/^\[/p' "$CONFIG_FILE" | grep -q "active = true"; then
    if ! ss -ulnp 2>/dev/null | grep -q ':67'; then
        exit 1
    fi
fi

# If all checks pass, the service is healthy
exit 0
