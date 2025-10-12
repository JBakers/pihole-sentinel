#!/bin/bash
STATE=$1
LOGFILE="/var/log/keepalived-notify.log"
NOTIFY_SCRIPT="/usr/local/bin/notify.sh"

timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

case $STATE in
    MASTER)
        echo "$(timestamp) - Transitioning to MASTER state. Enabling DHCP." >> "$LOGFILE"
        /usr/local/bin/dhcp_control.sh enable >> "$LOGFILE" 2>&1
        # Send gratuitous ARP to update network quickly
        arping -c 3 -I eth0 -s ${VIP_ADDRESS} ${NETWORK_GATEWAY} &>/dev/null  # Update with your VIP and gateway
        # Send notification
        [ -x "$NOTIFY_SCRIPT" ] && "$NOTIFY_SCRIPT" "MASTER" &
        ;;
    BACKUP)
        echo "$(timestamp) - Transitioning to BACKUP state. Disabling DHCP." >> "$LOGFILE"
        /usr/local/bin/dhcp_control.sh disable >> "$LOGFILE" 2>&1
        # Send notification
        [ -x "$NOTIFY_SCRIPT" ] && "$NOTIFY_SCRIPT" "BACKUP" &
        ;;
    FAULT)
        echo "$(timestamp) - Transitioning to FAULT state. Disabling DHCP." >> "$LOGFILE"
        /usr/local/bin/dhcp_control.sh disable >> "$LOGFILE" 2>&1
        # Send notification
        [ -x "$NOTIFY_SCRIPT" ] && "$NOTIFY_SCRIPT" "FAULT" &
        ;;
esac
