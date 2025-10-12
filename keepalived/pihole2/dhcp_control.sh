#!/bin/bash

CONFIG_FILE="/etc/pihole/pihole.toml"

# Functie om DHCP in te schakelen
enable_dhcp() {
    echo "DHCP inschakelen in $CONFIG_FILE..."
    # Wijzigt 'active = false' naar 'active = true' alleen onder de [dhcp] header
    sed -i '/^\[dhcp\]/,/^\[/ s/active = false/active = true/' "$CONFIG_FILE"
    systemctl restart pihole-FTL.service
    echo "DHCP ingeschakeld."
}

# Functie om DHCP uit te schakelen
disable_dhcp() {
    echo "DHCP uitschakelen in $CONFIG_FILE..."
    # Wijzigt 'active = true' naar 'active = false' alleen onder de [dhcp] header
    sed -i '/^\[dhcp\]/,/^\[/ s/active = true/active = false/' "$CONFIG_FILE"
    systemctl restart pihole-FTL.service
    echo "DHCP uitgeschakeld."
}

case "$1" in
    enable)
        enable_dhcp
        ;;
    disable)
        disable_dhcp
        ;;
    *)
        echo "Gebruik: $0 {enable|disable}"
        exit 1
        ;;
esac

exit 0
