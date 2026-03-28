#!/bin/bash

CONFIG_FILE="/etc/pihole/pihole.toml"

# Helper: return 0 (true) when DHCP is currently active
dhcp_is_active() {
    sed -n '/^\[dhcp\]/,/^\[/p' "$CONFIG_FILE" 2>/dev/null | grep -q "active = true"
}

LOCK_FILE="/var/lock/pihole-dhcp-control.lock"

# Function to enable DHCP
enable_dhcp() {
    (
        flock -x -w 10 200 || { echo "Could not acquire lock"; return 1; }
        # Idempotency check: skip restart when DHCP is already active.
        # Without this check a MASTER transition → FTL restart → health-check
        # failure → secondary takes over → FTL restart on secondary → primary
        # recovers → preempts back → FTL restart loop that can freeze the node.
        if dhcp_is_active; then
            echo "DHCP is already enabled, no change needed."
            return 0
        fi
        echo "Enabling DHCP in $CONFIG_FILE..."
        # Changes 'active = false' to 'active = true' only under the [dhcp] header
        sed -i '/^\[dhcp\]/,/^\[/ s/active = false/active = true/' "$CONFIG_FILE"
        systemctl restart pihole-FTL.service
        echo "DHCP enabled."
    ) 200>"$LOCK_FILE"
}

# Function to disable DHCP
disable_dhcp() {
    (
        flock -x -w 10 200 || { echo "Could not acquire lock"; return 1; }
        # Idempotency check: skip restart when DHCP is already inactive.
        if ! dhcp_is_active; then
            echo "DHCP is already disabled, no change needed."
            return 0
        fi
        echo "Disabling DHCP in $CONFIG_FILE..."
        # Changes 'active = true' to 'active = false' only under the [dhcp] header
        sed -i '/^\[dhcp\]/,/^\[/ s/active = true/active = false/' "$CONFIG_FILE"
        systemctl restart pihole-FTL.service
        echo "DHCP disabled."
    ) 200>"$LOCK_FILE"
}

case "$1" in
    enable)
        enable_dhcp
        ;;
    disable)
        disable_dhcp
        ;;
    *)
        echo "Usage: $0 {enable|disable}"
        exit 1
        ;;
esac

exit 0
