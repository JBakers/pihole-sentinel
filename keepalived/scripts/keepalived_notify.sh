#!/bin/bash
STATE=$1
LOGFILE="/var/log/keepalived-notify.log"

timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

# Load environment (contains DHCP_ENABLED, VIP_ADDRESS, etc.)
if [ -f /etc/keepalived/.env ]; then
    # shellcheck source=/dev/null
    source /etc/keepalived/.env
fi

# Helper: run dhcp_control.sh only when DHCP failover is enabled
dhcp_action() {
    local action="$1"
    if [ "${DHCP_ENABLED}" = "true" ]; then
        /usr/local/bin/dhcp_control.sh "$action" >> "$LOGFILE" 2>&1
    else
        echo "$(timestamp) - DHCP failover disabled, skipping dhcp_control $action" >> "$LOGFILE"
    fi
}

case $STATE in
    MASTER)
        echo "$(timestamp) - Transitioning to MASTER state." >> "$LOGFILE"
        dhcp_action enable
        # Send gratuitous ARP to update network quickly
        INTERFACE="${INTERFACE:-eth0}"
        if [ -n "$VIP_ADDRESS" ] && [ -n "$NETWORK_GATEWAY" ]; then
            arping -c 3 -I "${INTERFACE}" -s "${VIP_ADDRESS}" "${NETWORK_GATEWAY}" &>/dev/null || true
        fi
        # Notifications are handled by the monitor service
        ;;
    BACKUP)
        echo "$(timestamp) - Transitioning to BACKUP state." >> "$LOGFILE"
        dhcp_action disable
        # Notifications are handled by the monitor service
        ;;
    FAULT)
        echo "$(timestamp) - Transitioning to FAULT state." >> "$LOGFILE"
        dhcp_action disable
        # Notifications are handled by the monitor service
        ;;
esac
