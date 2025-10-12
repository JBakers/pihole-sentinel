#!/bin/bash

CONFIG_FILE="/etc/pihole/pihole.toml"

# Function to enable DHCP
enable_dhcp() {
    echo "Enabling DHCP in $CONFIG_FILE..."
    # Changes 'active = false' to 'active = true' only under the [dhcp] header
    sed -i '/^\[dhcp\]/,/^\[/ s/active = false/active = true/' "$CONFIG_FILE"
    systemctl restart pihole-FTL.service
    echo "DHCP enabled."
}

# Function to disable DHCP
disable_dhcp() {
    echo "Disabling DHCP in $CONFIG_FILE..."
    # Changes 'active = true' to 'active = false' only under the [dhcp] header
    sed -i '/^\[dhcp\]/,/^\[/ s/active = true/active = false/' "$CONFIG_FILE"
    systemctl restart pihole-FTL.service
    echo "DHCP disabled."
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
