#!/bin/bash
STATE=$1
LOGFILE="/var/log/keepalived-notify.log"

timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

case $STATE in
    MASTER)
        echo "$(timestamp) - Transitioning to MASTER state. Enabling DHCP." >> "$LOGFILE"
        /usr/local/bin/dhcp_control.sh enable >> "$LOGFILE" 2>&1
        # Send gratuitous ARP to update network quickly
        # Load interface from environment, fallback to eth0 if not set
        INTERFACE="${INTERFACE:-eth0}"
        if [ -n "$VIP_ADDRESS" ] && [ -n "$NETWORK_GATEWAY" ]; then
            arping -c 3 -I "${INTERFACE}" -s "${VIP_ADDRESS}" "${NETWORK_GATEWAY}" &>/dev/null || true
        fi
        # Notifications are handled by the monitor service
        ;;
    BACKUP)
        echo "$(timestamp) - Transitioning to BACKUP state. Disabling DHCP." >> "$LOGFILE"
        /usr/local/bin/dhcp_control.sh disable >> "$LOGFILE" 2>&1
        # Notifications are handled by the monitor service
        ;;
    FAULT)
        echo "$(timestamp) - Transitioning to FAULT state. Disabling DHCP." >> "$LOGFILE"
        /usr/local/bin/dhcp_control.sh disable >> "$LOGFILE" 2>&1
        # Notifications are handled by the monitor service
        ;;
esac
