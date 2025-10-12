#!/bin/bash
# Pi-hole Sentinel Notification System
# Supports: Telegram, Discord, Pushover, Ntfy, and custom webhooks

# Configuration file (create this with your credentials)
CONFIG_FILE="/etc/pihole-sentinel/notify.conf"

# Default event settings (can be overridden in config)
NOTIFY_FAILOVER="${NOTIFY_FAILOVER:-true}"
NOTIFY_RECOVERY="${NOTIFY_RECOVERY:-true}"
NOTIFY_FAULT="${NOTIFY_FAULT:-true}"
NOTIFY_STARTUP="${NOTIFY_STARTUP:-false}"

# Load configuration
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Function to send Telegram notification
send_telegram() {
    local message="$1"
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="${TELEGRAM_CHAT_ID}" \
            -d text="${message}" \
            -d parse_mode="HTML" \
            > /dev/null 2>&1
    fi
}

# Function to send Discord notification
send_discord() {
    local message="$1"
    local color="$2"  # Decimal color (e.g., 16711680 for red, 65280 for green)
    
    if [ -n "$DISCORD_WEBHOOK_URL" ]; then
        local json_payload=$(cat <<EOF
{
  "embeds": [{
    "title": "🛡️ Pi-hole Sentinel Alert",
    "description": "${message}",
    "color": ${color},
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)",
    "footer": {
      "text": "Pi-hole Sentinel HA Monitor"
    }
  }]
}
EOF
)
        curl -s -H "Content-Type: application/json" \
            -X POST -d "$json_payload" \
            "$DISCORD_WEBHOOK_URL" \
            > /dev/null 2>&1
    fi
}

# Function to send Pushover notification
send_pushover() {
    local message="$1"
    local priority="$2"  # -2 to 2 (2 requires acknowledgment)
    
    if [ -n "$PUSHOVER_USER_KEY" ] && [ -n "$PUSHOVER_APP_TOKEN" ]; then
        curl -s -X POST https://api.pushover.net/1/messages.json \
            -d "token=${PUSHOVER_APP_TOKEN}" \
            -d "user=${PUSHOVER_USER_KEY}" \
            -d "message=${message}" \
            -d "title=Pi-hole Sentinel" \
            -d "priority=${priority}" \
            > /dev/null 2>&1
    fi
}

# Function to send Ntfy notification
send_ntfy() {
    local message="$1"
    local priority="$2"  # max, high, default, low, min
    
    if [ -n "$NTFY_TOPIC" ]; then
        local ntfy_server="${NTFY_SERVER:-https://ntfy.sh}"
        curl -s -X POST "${ntfy_server}/${NTFY_TOPIC}" \
            -H "Title: Pi-hole Sentinel Alert" \
            -H "Priority: ${priority}" \
            -H "Tags: shield,pihole" \
            -d "${message}" \
            > /dev/null 2>&1
    fi
}

# Function to send custom webhook
send_webhook() {
    local message="$1"
    local state="$2"
    
    if [ -n "$CUSTOM_WEBHOOK_URL" ]; then
        local json_payload=$(cat <<EOF
{
  "service": "pihole-sentinel",
  "hostname": "$(hostname)",
  "state": "${state}",
  "message": "${message}",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
}
EOF
)
        curl -s -H "Content-Type: application/json" \
            -X POST -d "$json_payload" \
            "$CUSTOM_WEBHOOK_URL" \
            > /dev/null 2>&1
    fi
}

# Main notification function
notify() {
    local state="$1"
    local hostname=$(hostname)
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    local message=""
    local color=""
    local priority=""
    local should_notify=false
    
    case $state in
        MASTER)
            # Check if this is recovery (BACKUP->MASTER) or startup
            if [ "$NOTIFY_RECOVERY" = "true" ]; then
                should_notify=true
            fi
            message="🟢 <b>${hostname}</b> is now MASTER\n⏰ ${timestamp}\n✅ DHCP server enabled\n🌐 Virtual IP active"
            color="65280"  # Green
            priority="high"
            ;;
        BACKUP)
            # This means another node took over (failover event)
            if [ "$NOTIFY_FAILOVER" = "true" ]; then
                should_notify=true
            fi
            message="🟡 <b>${hostname}</b> is now BACKUP\n⏰ ${timestamp}\n⏸️ DHCP server disabled\n👀 Monitoring MASTER"
            color="16776960"  # Yellow
            priority="default"
            ;;
        FAULT)
            if [ "$NOTIFY_FAULT" = "true" ]; then
                should_notify=true
            fi
            message="🔴 <b>${hostname}</b> entered FAULT state\n⏰ ${timestamp}\n❌ DHCP server disabled\n⚠️ Service issues detected"
            color="16711680"  # Red
            priority="2"  # Emergency for Pushover
            ;;
        STARTUP)
            if [ "$NOTIFY_STARTUP" = "true" ]; then
                should_notify=true
            fi
            message="ℹ️ <b>${hostname}</b> monitoring started\n⏰ ${timestamp}\n🚀 Pi-hole Sentinel active"
            color="3447003"  # Blue
            priority="default"
            ;;
        *)
            message="ℹ️ <b>${hostname}</b> state changed to ${state}\n⏰ ${timestamp}"
            color="3447003"  # Blue
            priority="default"
            should_notify=true
            ;;
    esac
    
    # Only send if event is enabled
    if [ "$should_notify" = "true" ]; then
        send_telegram "$message"
        send_discord "$message" "$color"
        send_pushover "$message" "$priority"
        send_ntfy "$message" "$priority"
        send_webhook "$message" "$state"
    fi
}

# Execute if called directly with state parameter
if [ $# -eq 1 ]; then
    notify "$1"
fi
