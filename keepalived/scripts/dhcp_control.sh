#!/bin/bash

CONFIG_FILE="/etc/pihole/pihole.toml"

# Helper: return 0 (true) when DHCP is currently active
dhcp_is_active() {
    sed -n '/^\[dhcp\]/,/^\[/p' "$CONFIG_FILE" 2>/dev/null | grep -q "active = true"
}

# Helper: return 0 (true) when port 67 is bound
port67_bound() {
    ss -ulnp 2>/dev/null | grep -qE ':67\b'
}

LOCK_FILE="/var/lock/pihole-dhcp-control.lock"

# Function to enable DHCP
enable_dhcp() {
    (
        flock -x -w 10 200 || { echo "Could not acquire lock"; return 1; }

        # Already fully enabled (config + port)
        if dhcp_is_active && port67_bound; then
            echo "DHCP is already enabled, no change needed."
            return 0
        fi

        # Update config if needed
        if ! dhcp_is_active; then
            echo "Enabling DHCP in $CONFIG_FILE..."
            sed -i '/^\[dhcp\]/,/^\[/ s/active = false/active = true/' "$CONFIG_FILE"
        fi

        # Wait for FTL inotify to bind port 67
        for i in $(seq 15); do
            if port67_bound; then
                echo "DHCP enabled (port 67 bound)."
                return 0
            fi
            sleep 1
        done

        # Fallback: FTL missed the inotify event — restart to force reload
        echo "inotify did not trigger, restarting FTL..."
        systemctl restart pihole-FTL
        for i in $(seq 10); do
            if port67_bound; then
                echo "DHCP enabled (port 67 bound after FTL restart)."
                return 0
            fi
            sleep 1
        done
        echo "WARNING: DHCP enabled in config but port 67 not yet bound after 25s."
        echo "DHCP enabled."
    ) 200>"$LOCK_FILE"
}

# Function to disable DHCP
disable_dhcp() {
    (
        flock -x -w 10 200 || { echo "Could not acquire lock"; return 1; }

        # Already fully disabled (config + port)
        if ! dhcp_is_active && ! port67_bound; then
            echo "DHCP is already disabled, no change needed."
            return 0
        fi

        # Update config if needed
        if dhcp_is_active; then
            echo "Disabling DHCP in $CONFIG_FILE..."
            sed -i '/^\[dhcp\]/,/^\[/ s/active = true/active = false/' "$CONFIG_FILE"
        fi

        # Wait for FTL inotify to release port 67
        for i in $(seq 15); do
            if ! port67_bound; then
                echo "DHCP disabled (port 67 released)."
                return 0
            fi
            sleep 1
        done

        # Fallback: FTL missed the inotify event — restart to force reload
        echo "inotify did not trigger, restarting FTL..."
        systemctl restart pihole-FTL
        for i in $(seq 10); do
            if ! port67_bound; then
                echo "DHCP disabled (port 67 released after FTL restart)."
                return 0
            fi
            sleep 1
        done
        echo "WARNING: DHCP disabled in config but port 67 still bound after 25s."
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
