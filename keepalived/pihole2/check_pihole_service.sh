#!/bin/bash

CONFIG_FILE="/etc/pihole/pihole.toml"

# 1. Controleer of de FTL service überhaupt actief is.
if ! systemctl is-active --quiet pihole-FTL; then
    exit 1
fi

# Voeg een korte pauze toe om FTL de tijd te geven volledig te initialiseren.
sleep 1

# 2. Controleer of de DNS-functionaliteit lokaal reageert.
if ! timeout 2 dig @127.0.0.1 pi.hole +short &>/dev/null; then
    exit 1
fi

# 3. Slimme DHCP-check: controleer alleen de DHCP-poort als de service geconfigureerd staat als actief IN DE DHCP SECTIE.
if sed -n '/^\[dhcp\]/,/^\[/p' "$CONFIG_FILE" | grep -q "active = true"; then
    if ! ss -ulnp 2>/dev/null | grep -q ':67'; then
        exit 1
    fi
fi

# Als alle checks slagen, is de service gezond.
exit 0
