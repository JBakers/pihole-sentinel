#!/bin/bash
#
# Pi-hole Configuration Synchronization Script
# ============================================
#
# This script synchronizes Pi-hole configurations between Primary and Secondary nodes
# to ensure both have identical settings (adlists, whitelists, blacklists, groups, etc.)
#
# Usage:
#   ./sync-pihole-config.sh [primary|secondary]
#
# When run on PRIMARY: Syncs config TO secondary
# When run on SECONDARY: Syncs config FROM primary
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration — IPs are loaded from /etc/keepalived/.env (deployed by setup.py)
# These defaults are only used if .env is missing (manual install)
PRIMARY_IP="${PRIMARY_IP:-}"
SECONDARY_IP="${SECONDARY_IP:-}"
PIHOLE_DIR="/etc/pihole"
BACKUP_DIR="/root/pihole-sync-backup"

# Sync configuration file (deployed by setup.py)
SYNC_CONF="/etc/pihole-sentinel/sync.conf"
if [ -f "$SYNC_CONF" ]; then
    # Parse key=value safely (no source to avoid arbitrary code execution)
    while IFS='=' read -r key value; do
        key=$(echo "$key" | tr -d '[:space:]')
        value=$(echo "$value" | tr -d '[:space:]' | tr -d '"')
        case "$key" in
            PRIMARY_IP)        PRIMARY_IP="$value" ;;
            SECONDARY_IP)      SECONDARY_IP="$value" ;;
            SYNC_INTERVAL_MINUTES) SYNC_INTERVAL_MINUTES="$value" ;;
            SYNC_GRAVITY)          SYNC_GRAVITY="$value" ;;
            SYNC_CUSTOM_DNS)       SYNC_CUSTOM_DNS="$value" ;;
            SYNC_CNAME)            SYNC_CNAME="$value" ;;
            SYNC_DHCP_LEASES)      SYNC_DHCP_LEASES="$value" ;;
            SYNC_CONFIG)           SYNC_CONFIG_DHCP="$value"; SYNC_CONFIG_DNS="$value" ;;
            SYNC_CONFIG_DHCP)      SYNC_CONFIG_DHCP="$value" ;;
            SYNC_CONFIG_DNS)       SYNC_CONFIG_DNS="$value" ;;
            SYNC_CONFIG_DHCP_EXCLUDE_ACTIVE) SYNC_CONFIG_DHCP_EXCLUDE_ACTIVE="$value" ;;
            SYNC_RESTART_FTL)      SYNC_RESTART_FTL="$value" ;;
            SYNC_MAX_BACKUPS)      SYNC_MAX_BACKUPS="$value" ;;
            SYNC_CONFIG_DNS_EXCLUDE_UPSTREAMS) SYNC_CONFIG_DNS_EXCLUDE_UPSTREAMS="$value" ;;
        esac
    done < <(grep -v '^\s*#' "$SYNC_CONF" | grep '=')
fi

# Defaults (matching nebula-sync feature parity)
SYNC_GRAVITY="${SYNC_GRAVITY:-true}"
SYNC_CUSTOM_DNS="${SYNC_CUSTOM_DNS:-true}"
SYNC_CNAME="${SYNC_CNAME:-true}"
SYNC_DHCP_LEASES="${SYNC_DHCP_LEASES:-true}"
SYNC_CONFIG_DHCP="${SYNC_CONFIG_DHCP:-true}"
SYNC_CONFIG_DHCP_EXCLUDE_ACTIVE="${SYNC_CONFIG_DHCP_EXCLUDE_ACTIVE:-true}"
SYNC_CONFIG_DNS="${SYNC_CONFIG_DNS:-true}"
SYNC_RESTART_FTL="${SYNC_RESTART_FTL:-true}"
SYNC_MAX_BACKUPS="${SYNC_MAX_BACKUPS:-3}"
SYNC_CONFIG_DNS_EXCLUDE_UPSTREAMS="${SYNC_CONFIG_DNS_EXCLUDE_UPSTREAMS:-true}"

# Determine node type
NODE_TYPE=""
if [ -f "/etc/keepalived/.env" ]; then
    # Parse IPs and node state from keepalived env
    while IFS='=' read -r key value; do
        key=$(echo "$key" | tr -d '[:space:]')
        value=$(echo "$value" | tr -d '[:space:]' | tr -d '"')
        case "$key" in
            NODE_STATE)    NODE_TYPE="$value" ;;
            PRIMARY_IP)    PRIMARY_IP="${PRIMARY_IP:-$value}" ;;
            SECONDARY_IP)  SECONDARY_IP="${SECONDARY_IP:-$value}" ;;
        esac
    done < <(grep -v '^\s*#' /etc/keepalived/.env | grep '=')
else
    echo -e "${YELLOW}Warning: Could not determine node type from /etc/keepalived/.env${NC}"
    echo "Please specify node type as argument: primary or secondary"
    NODE_TYPE="$1"
fi

# Validate IPs are set
if [ -z "$PRIMARY_IP" ] || [ -z "$SECONDARY_IP" ]; then
    echo -e "${RED}[ERROR] PRIMARY_IP or SECONDARY_IP not set.${NC}"
    echo "Deploy sync via setup.py, or set IPs in /etc/pihole-sentinel/sync.conf"
    exit 1
fi

# Convert to lowercase
NODE_TYPE=$(echo "$NODE_TYPE" | tr '[:upper:]' '[:lower:]')

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_pihole_running() {
    if ! systemctl is-active --quiet pihole-FTL; then
        log_error "Pi-hole FTL service is not running!"
        return 1
    fi
    return 0
}

create_backup() {
    local backup_name="pihole-backup-$(date +%Y%m%d-%H%M%S)"
    log_info "Creating backup: $backup_name"
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup important files
    tar czf "$BACKUP_DIR/$backup_name.tar.gz" \
        "$PIHOLE_DIR/gravity.db" \
        "$PIHOLE_DIR/custom.list" \
        "$PIHOLE_DIR/pihole.toml" \
        2>/dev/null || true
    
    # Keep only last N backups (configurable via SYNC_MAX_BACKUPS, default 3)
    cd "$BACKUP_DIR"
    ls -t pihole-backup-*.tar.gz | tail -n +$((SYNC_MAX_BACKUPS + 1)) | xargs -r rm
    
    log_info "Backup created successfully"
}

sync_from_primary() {
    log_info "Syncing configuration FROM primary ($PRIMARY_IP)..."
    
    # Create backup before sync
    create_backup
    
    # Stop Pi-hole temporarily (only if we'll restart it)
    if [ "$SYNC_RESTART_FTL" = "true" ]; then
        log_info "Stopping Pi-hole..."
        systemctl stop pihole-FTL
        local ftl_was_stopped=true
    fi
    
    # Sync gravity database (contains all lists, groups, clients, etc.)
    if [ "$SYNC_GRAVITY" = "true" ]; then
        log_info "Syncing gravity database..."
        rsync -avz --progress "root@${PRIMARY_IP}:${PIHOLE_DIR}/gravity.db" "${PIHOLE_DIR}/" || {
            log_error "Failed to sync gravity.db"
            if [ "$ftl_was_stopped" = "true" ]; then
                systemctl start pihole-FTL
            fi
            exit 1
        }
    else
        log_info "Skipping gravity database (SYNC_GRAVITY=false)"
    fi
    
    # Sync custom DNS records
    if [ "$SYNC_CUSTOM_DNS" = "true" ]; then
        log_info "Syncing custom DNS records..."
        if ssh "root@${PRIMARY_IP}" "[ -f ${PIHOLE_DIR}/custom.list ]"; then
            rsync -avz --progress "root@${PRIMARY_IP}:${PIHOLE_DIR}/custom.list" "${PIHOLE_DIR}/" || {
                log_error "Failed to sync custom.list - network or permission issue"
                if [ "$ftl_was_stopped" = "true" ]; then
                    systemctl start pihole-FTL
                fi
                exit 1
            }
        else
            log_warn "custom.list does not exist on primary (skipping)"
        fi
    else
        log_info "Skipping custom DNS records (SYNC_CUSTOM_DNS=false)"
    fi
    
    # Sync CNAME records
    if [ "$SYNC_CNAME" = "true" ]; then
        if ssh "root@${PRIMARY_IP}" "[ -f ${PIHOLE_DIR}/05-pihole-custom-cname.conf ]"; then
            rsync -avz --progress "root@${PRIMARY_IP}:${PIHOLE_DIR}/05-pihole-custom-cname.conf" "${PIHOLE_DIR}/" || {
                log_error "Failed to sync CNAME records - network or permission issue"
                if [ "$ftl_was_stopped" = "true" ]; then
                    systemctl start pihole-FTL
                fi
                exit 1
            }
        else
            log_warn "No custom CNAME records on primary (skipping)"
        fi
    else
        log_info "Skipping CNAME records (SYNC_CNAME=false)"
    fi
    
    # Sync DHCP static leases
    if [ "$SYNC_DHCP_LEASES" = "true" ]; then
        log_info "Syncing DHCP static leases..."
        if ssh "root@${PRIMARY_IP}" "[ -f ${PIHOLE_DIR}/dhcp.leases ]"; then
            rsync -avz --progress "root@${PRIMARY_IP}:${PIHOLE_DIR}/dhcp.leases" "${PIHOLE_DIR}/" || {
                log_warn "Failed to sync dhcp.leases"
            }
        fi
    else
        log_info "Skipping DHCP leases (SYNC_DHCP_LEASES=false)"
    fi
    
    # Sync Pi-hole DHCP configuration from pihole.toml
    # (Only the [dhcp] section — never overwrites the whole file)
    if [ "$SYNC_CONFIG_DHCP" = "true" ] || [ "$SYNC_CONFIG_DNS" = "true" ]; then
        log_info "Downloading remote pihole.toml for selective sync..."
        rsync -avz --progress "root@${PRIMARY_IP}:${PIHOLE_DIR}/pihole.toml" "/tmp/pihole.toml.remote" || {
            log_warn "Failed to download pihole.toml"
        }
    fi

    if [ "$SYNC_CONFIG_DHCP" = "true" ] && [ -f "/tmp/pihole.toml.remote" ]; then
        log_info "Syncing DHCP configuration..."

        # Extract [dhcp] section from remote (everything between [dhcp] and next [section])
        sed -n '/^\[dhcp\]/,/^\[/{ /^\[dhcp\]/p; /^\[/!p; }' "/tmp/pihole.toml.remote" > /tmp/dhcp_remote.toml

        if [ -s /tmp/dhcp_remote.toml ]; then
            # Preserve local DHCP active state
            if [ "$SYNC_CONFIG_DHCP_EXCLUDE_ACTIVE" = "true" ]; then
                local_dhcp_active=$(sed -n '/^\[dhcp\]/,/^\[/{ /^active = /p; }' "${PIHOLE_DIR}/pihole.toml" | head -n1)
            fi

            # Replace local [dhcp] section with remote
            # 1) Delete old [dhcp] section from local
            sed -i '/^\[dhcp\]/,/^\[/{ /^\[dhcp\]/d; /^\[/!d; }' "${PIHOLE_DIR}/pihole.toml"
            # 2) Find insertion point (line before the section that followed [dhcp])
            # We insert just before the next section header after where [dhcp] was
            # Simpler: append [dhcp] block at the end (pihole-FTL tolerates section order)
            printf '\n' >> "${PIHOLE_DIR}/pihole.toml"
            cat /tmp/dhcp_remote.toml >> "${PIHOLE_DIR}/pihole.toml"

            # Restore local DHCP active state
            if [ "$SYNC_CONFIG_DHCP_EXCLUDE_ACTIVE" = "true" ] && [ -n "$local_dhcp_active" ]; then
                sed -i "/^\[dhcp\]/,/^\[/ s/^active = .*/$local_dhcp_active/" "${PIHOLE_DIR}/pihole.toml"
                log_info "Preserved local DHCP active state: $local_dhcp_active"
            fi
            log_info "DHCP configuration synced"
        fi
        rm -f /tmp/dhcp_remote.toml
    elif [ "$SYNC_CONFIG_DHCP" != "true" ]; then
        log_info "Skipping DHCP config (SYNC_CONFIG_DHCP=false)"
    fi

    # Sync DNS configuration from pihole.toml (hosts/upstream settings)
    if [ "$SYNC_CONFIG_DNS" = "true" ] && [ -f "/tmp/pihole.toml.remote" ]; then
        log_info "Syncing DNS configuration..."

        # Extract [dns] section from remote
        sed -n '/^\[dns\]/,/^\[/{ /^\[dns\]/p; /^\[/!p; }' "/tmp/pihole.toml.remote" > /tmp/dns_remote.toml

        if [ -s /tmp/dns_remote.toml ]; then
            # Preserve local DNS settings that are node-specific
            local_dns_listening=$(sed -n '/^\[dns\]/,/^\[/{ /^listeningMode = /p; }' "${PIHOLE_DIR}/pihole.toml" | head -n1)
            if [ "$SYNC_CONFIG_DNS_EXCLUDE_UPSTREAMS" = "true" ]; then
                local_dns_upstreams=$(sed -n '/^\[dns\]/,/^\[/{ /^upstreams = /p; }' "${PIHOLE_DIR}/pihole.toml" | head -n1)
            fi

            # Replace local [dns] section with remote
            sed -i '/^\[dns\]/,/^\[/{ /^\[dns\]/d; /^\[/!d; }' "${PIHOLE_DIR}/pihole.toml"
            printf '\n' >> "${PIHOLE_DIR}/pihole.toml"
            cat /tmp/dns_remote.toml >> "${PIHOLE_DIR}/pihole.toml"

            # Restore node-specific DNS settings
            if [ -n "$local_dns_listening" ]; then
                sed -i "/^\[dns\]/,/^\[/ s/^listeningMode = .*/$local_dns_listening/" "${PIHOLE_DIR}/pihole.toml"
            fi
            if [ "$SYNC_CONFIG_DNS_EXCLUDE_UPSTREAMS" = "true" ] && [ -n "$local_dns_upstreams" ]; then
                sed -i "/^\[dns\]/,/^\[/ s/^upstreams = .*/$local_dns_upstreams/" "${PIHOLE_DIR}/pihole.toml"
                log_info "Preserved local DNS upstreams: $local_dns_upstreams"
            fi
            log_info "DNS configuration synced"
        fi
        rm -f /tmp/dns_remote.toml
    elif [ "$SYNC_CONFIG_DNS" != "true" ]; then
        log_info "Skipping DNS config (SYNC_CONFIG_DNS=false)"
    fi

    # Cleanup remote toml
    rm -f /tmp/pihole.toml.remote
    
    # Set correct permissions
    chown pihole:pihole "${PIHOLE_DIR}/gravity.db" 2>/dev/null || true
    chown pihole:pihole "${PIHOLE_DIR}/custom.list" 2>/dev/null || true
    chown root:root "${PIHOLE_DIR}/pihole.toml" 2>/dev/null || true
    chmod 644 "${PIHOLE_DIR}/gravity.db" 2>/dev/null || true
    chmod 644 "${PIHOLE_DIR}/custom.list" 2>/dev/null || true
    chmod 644 "${PIHOLE_DIR}/pihole.toml" 2>/dev/null || true
    
    # Restart Pi-hole
    log_info "Restarting Pi-hole..."
    systemctl start pihole-FTL
    
    # Wait for FTL to start
    sleep 3
    
    if check_pihole_running; then
        log_info "✓ Sync completed successfully!"
        log_info "✓ Pi-hole is running"
        
        # Show stats
        pihole status
    else
        log_error "Pi-hole failed to start after sync!"
        log_error "Attempting to restore from backup..."
        restore_from_backup
        exit 1
    fi
}

sync_to_secondary() {
    log_info "Syncing configuration TO secondary ($SECONDARY_IP)..."
    
    if ! check_pihole_running; then
        log_error "Primary Pi-hole is not running. Cannot sync."
        exit 1
    fi
    
    # Test connection to secondary
    if ! ssh -o ConnectTimeout=5 "root@${SECONDARY_IP}" "echo Connected" &>/dev/null; then
        log_error "Cannot connect to secondary Pi-hole at $SECONDARY_IP"
        exit 1
    fi
    
    # Ask secondary to create backup (with rotation to prevent disk full)
    log_info "Creating backup on secondary (keeping last ${SYNC_MAX_BACKUPS})..."
    ssh "root@${SECONDARY_IP}" "mkdir -p $BACKUP_DIR && \
        tar czf $BACKUP_DIR/pihole-backup-\$(date +%Y%m%d-%H%M%S).tar.gz \
        $PIHOLE_DIR/gravity.db $PIHOLE_DIR/custom.list $PIHOLE_DIR/pihole.toml 2>/dev/null || true && \
        cd $BACKUP_DIR && ls -t pihole-backup-*.tar.gz 2>/dev/null | tail -n +$((SYNC_MAX_BACKUPS + 1)) | xargs -r rm"
    
    # Stop Pi-hole on secondary (only if restart enabled)
    if [ "$SYNC_RESTART_FTL" = "true" ]; then
        log_info "Stopping Pi-hole on secondary..."
        ssh "root@${SECONDARY_IP}" "systemctl stop pihole-FTL"
    fi
    
    # Push gravity database
    if [ "$SYNC_GRAVITY" = "true" ]; then
        log_info "Pushing gravity database..."
        rsync -avz --progress "${PIHOLE_DIR}/gravity.db" "root@${SECONDARY_IP}:${PIHOLE_DIR}/" || {
            log_error "Failed to push gravity.db"
            ssh "root@${SECONDARY_IP}" "systemctl start pihole-FTL"
            exit 1
        }
    else
        log_info "Skipping gravity database (SYNC_GRAVITY=false)"
    fi
    
    # Push custom DNS records
    if [ "$SYNC_CUSTOM_DNS" = "true" ]; then
        log_info "Pushing custom DNS records..."
        rsync -avz --progress "${PIHOLE_DIR}/custom.list" "root@${SECONDARY_IP}:${PIHOLE_DIR}/" 2>/dev/null || {
            log_warn "No custom.list to push"
        }
    else
        log_info "Skipping custom DNS records (SYNC_CUSTOM_DNS=false)"
    fi
    
    # Push CNAME records
    if [ "$SYNC_CNAME" = "true" ]; then
        rsync -avz --progress "${PIHOLE_DIR}/05-pihole-custom-cname.conf" "root@${SECONDARY_IP}:${PIHOLE_DIR}/" 2>/dev/null || {
            log_warn "No custom CNAME records to push"
        }
    else
        log_info "Skipping CNAME records (SYNC_CNAME=false)"
    fi
    
    # Push DHCP static leases
    if [ "$SYNC_DHCP_LEASES" = "true" ]; then
        log_info "Pushing DHCP static leases..."
        if [ -f "${PIHOLE_DIR}/dhcp.leases" ]; then
            rsync -avz --progress "${PIHOLE_DIR}/dhcp.leases" "root@${SECONDARY_IP}:${PIHOLE_DIR}/" || {
                log_warn "Failed to push dhcp.leases"
            }
        fi
    else
        log_info "Skipping DHCP leases (SYNC_DHCP_LEASES=false)"
    fi
    
    # Push Pi-hole configuration (section-based to preserve node-specific settings)
    if [ "$SYNC_CONFIG_DHCP" = "true" ] || [ "$SYNC_CONFIG_DNS" = "true" ]; then
        log_info "Pushing Pi-hole configuration (section-based)..."

        # Copy primary toml to secondary as staging file
        rsync -avz --progress "${PIHOLE_DIR}/pihole.toml" "root@${SECONDARY_IP}:/tmp/pihole.toml.new"
        # Ensure staging file is writable by root (rsync may preserve source owner)
        ssh "root@${SECONDARY_IP}" "chown root:root /tmp/pihole.toml.new && chmod 600 /tmp/pihole.toml.new"

        # ━━━ Preserve ALL node-specific values on the secondary ━━━
        # SECURITY: all operations run in a single remote heredoc session.
        # Values never cross SSH as command args (no local $-expansion,
        # no ps/log exposure). Quoted heredoc prevents local variable expansion;
        # PIHOLE_DIR is passed via env to the remote shell.
        #
        # Preserved values:
        #   1. pwhash       — web API password (indented under [webserver.api])
        #   2. dhcp.active  — DHCP on/off state (top-level [dhcp])
        #   3. upstreams    — DNS upstream servers (top-level [dns])
        #   4. listeningMode — DNS listening scope (top-level [dns])
        #
        # We use python3 for the pwhash swap because the hash ($BALLOON-SHA256$...)
        # contains $, |, &, = which corrupt sed replacement strings.
        # For top-level [dhcp]/[dns] keys, sed is safe (simple values, no specials).

        ssh "root@${SECONDARY_IP}" PIHOLE_DIR="${PIHOLE_DIR}"             SYNC_DHCP="${SYNC_CONFIG_DHCP}"             SYNC_DHCP_EXCL="${SYNC_CONFIG_DHCP_EXCLUDE_ACTIVE}"             SYNC_DNS="${SYNC_CONFIG_DNS}"             SYNC_DNS_EXCL_UP="${SYNC_CONFIG_DNS_EXCLUDE_UPSTREAMS}"             bash << 'REMOTE_PRESERVE'
set -e
LOGFILE="/var/log/pihole-sync.log"
ts() { date '+%Y-%m-%d %H:%M:%S'; }
LIVE="$PIHOLE_DIR/pihole.toml"
STAGED="/tmp/pihole.toml.new"

# 1. Preserve pwhash (indented key, hash contains $, |, & — use python3 for safe swap)
pwhash_line=$(grep -m1 '^\s*pwhash = ' "$LIVE" || true)
if [ -n "$pwhash_line" ]; then
    python3 -c "
import sys
live_pw = sys.argv[1]
with open('$STAGED', 'r') as f:
    lines = f.readlines()
with open('$STAGED', 'w') as f:
    for line in lines:
        if line.lstrip().startswith('pwhash = '):
            f.write(live_pw + '
')
        else:
            f.write(line)
" "$pwhash_line"
    echo "$(ts) - Preserved secondary pwhash" >> "$LOGFILE"
fi

# 2. Preserve DHCP active state
if [ "$SYNC_DHCP" = "true" ] && [ "$SYNC_DHCP_EXCL" = "true" ]; then
    dhcp_active=$(sed -n '/^\[dhcp\]/,/^\[/{ /^active = /p; }' "$LIVE" | head -n1)
    if [ -n "$dhcp_active" ]; then
        sed -i "/^\[dhcp\]/,/^\[/ s/^active = .*/$dhcp_active/" "$STAGED"
        echo "$(ts) - Preserved secondary DHCP active: $dhcp_active" >> "$LOGFILE"
    fi
fi

# 3. Preserve DNS upstreams (e.g. local unbound 127.0.0.1#5335)
if [ "$SYNC_DNS" = "true" ] && [ "$SYNC_DNS_EXCL_UP" = "true" ]; then
    dns_up=$(sed -n '/^\[dns\]/,/^\[/{ /^upstreams = /p; }' "$LIVE" | head -n1)
    if [ -n "$dns_up" ]; then
        # upstreams value is a TOML array like ["x","y"] — use python3 for safe replace
        python3 -c "
import sys
live_up = sys.argv[1]
with open('$STAGED', 'r') as f:
    lines = f.readlines()
in_dns = False
with open('$STAGED', 'w') as f:
    for line in lines:
        stripped = line.strip()
        if stripped == '[dns]':
            in_dns = True
        elif stripped.startswith('[') and stripped != '[dns]':
            in_dns = False
        if in_dns and stripped.startswith('upstreams = '):
            f.write(live_up + '
')
        else:
            f.write(line)
" "$dns_up"
        echo "$(ts) - Preserved secondary DNS upstreams" >> "$LOGFILE"
    fi
fi

# 4. Preserve DNS listeningMode
if [ "$SYNC_DNS" = "true" ]; then
    dns_lm=$(sed -n '/^\[dns\]/,/^\[/{ /^listeningMode = /p; }' "$LIVE" | head -n1)
    if [ -n "$dns_lm" ]; then
        sed -i "/^\[dns\]/,/^\[/ s/^listeningMode = .*/$dns_lm/" "$STAGED"
        echo "$(ts) - Preserved secondary DNS listeningMode" >> "$LOGFILE"
    fi
fi

echo "$(ts) - All node-specific values preserved" >> "$LOGFILE"
REMOTE_PRESERVE
        log_info "Preserved secondary node-specific settings"

        ssh "root@${SECONDARY_IP}" "mv /tmp/pihole.toml.new ${PIHOLE_DIR}/pihole.toml"
        log_info "Pi-hole configuration pushed"
    else
        log_info "Skipping Pi-hole config (SYNC_CONFIG_DHCP and SYNC_CONFIG_DNS both false)"
    fi
    
    # Fix permissions on secondary
    ssh "root@${SECONDARY_IP}" "chown pihole:pihole ${PIHOLE_DIR}/gravity.db ${PIHOLE_DIR}/custom.list 2>/dev/null || true && \
        chown root:root ${PIHOLE_DIR}/pihole.toml 2>/dev/null || true && \
        chmod 644 ${PIHOLE_DIR}/gravity.db ${PIHOLE_DIR}/custom.list ${PIHOLE_DIR}/pihole.toml 2>/dev/null || true"
    
    # Start Pi-hole on secondary
    log_info "Starting Pi-hole on secondary..."
    ssh "root@${SECONDARY_IP}" "systemctl start pihole-FTL"
    
    # Wait and check
    sleep 3
    if ssh "root@${SECONDARY_IP}" "systemctl is-active --quiet pihole-FTL"; then
        log_info "✓ Sync to secondary completed successfully!"
        log_info "✓ Secondary Pi-hole is running"
    else
        log_error "Secondary Pi-hole failed to start after sync!"
        exit 1
    fi
}

restore_from_backup() {
    log_warn "Restoring from latest backup..."
    
    local latest_backup=$(ls -t "$BACKUP_DIR"/pihole-backup-*.tar.gz 2>/dev/null | head -n1)
    
    if [ -z "$latest_backup" ]; then
        log_error "No backup found to restore!"
        return 1
    fi
    
    log_info "Restoring from: $(basename $latest_backup)"
    tar xzf "$latest_backup" -C / 2>/dev/null || {
        log_error "Failed to restore backup"
        return 1
    }
    
    systemctl start pihole-FTL
    log_info "Backup restored"
}

show_diff() {
    log_info "Showing configuration differences..."
    
    local temp_dir=$(mktemp -d)
    
    # Get remote gravity.db stats
    ssh "root@${SECONDARY_IP}" "sqlite3 ${PIHOLE_DIR}/gravity.db 'SELECT COUNT(*) FROM adlist;'" > "$temp_dir/remote_adlist_count" 2>/dev/null || echo "0" > "$temp_dir/remote_adlist_count"
    ssh "root@${SECONDARY_IP}" "sqlite3 ${PIHOLE_DIR}/gravity.db 'SELECT COUNT(*) FROM domainlist WHERE type=0;'" > "$temp_dir/remote_whitelist_count" 2>/dev/null || echo "0" > "$temp_dir/remote_whitelist_count"
    ssh "root@${SECONDARY_IP}" "sqlite3 ${PIHOLE_DIR}/gravity.db 'SELECT COUNT(*) FROM domainlist WHERE type=1;'" > "$temp_dir/remote_blacklist_count" 2>/dev/null || echo "0" > "$temp_dir/remote_blacklist_count"
    
    # Get local gravity.db stats
    local_adlist=$(sqlite3 "${PIHOLE_DIR}/gravity.db" 'SELECT COUNT(*) FROM adlist;' 2>/dev/null || echo "0")
    local_whitelist=$(sqlite3 "${PIHOLE_DIR}/gravity.db" 'SELECT COUNT(*) FROM domainlist WHERE type=0;' 2>/dev/null || echo "0")
    local_blacklist=$(sqlite3 "${PIHOLE_DIR}/gravity.db" 'SELECT COUNT(*) FROM domainlist WHERE type=1;' 2>/dev/null || echo "0")
    
    remote_adlist=$(cat "$temp_dir/remote_adlist_count")
    remote_whitelist=$(cat "$temp_dir/remote_whitelist_count")
    remote_blacklist=$(cat "$temp_dir/remote_blacklist_count")
    
    echo ""
    echo "Configuration Comparison:"
    echo "========================="
    printf "%-20s %10s %10s\n" "Item" "Primary" "Secondary"
    printf "%-20s %10s %10s\n" "----" "-------" "---------"
    printf "%-20s %10d %10d\n" "Adlists" "$local_adlist" "$remote_adlist"
    printf "%-20s %10d %10d\n" "Whitelist" "$local_whitelist" "$remote_whitelist"
    printf "%-20s %10d %10d\n" "Blacklist" "$local_blacklist" "$remote_blacklist"
    echo ""
    
    if [ "$local_adlist" != "$remote_adlist" ] || [ "$local_whitelist" != "$remote_whitelist" ] || [ "$local_blacklist" != "$remote_blacklist" ]; then
        log_warn "Configurations are OUT OF SYNC"
    else
        log_info "Configurations are IN SYNC"
    fi
    
    rm -rf "$temp_dir"
}

# Main script logic
case "$NODE_TYPE" in
    master|primary)
        log_info "Running as PRIMARY node"
        
        if [ "$1" == "--diff" ]; then
            show_diff
        elif [ "$1" == "--auto" ]; then
            log_info "Auto-sync mode enabled"
            sync_to_secondary
        else
            echo ""
            echo "Pi-hole Configuration Sync - PRIMARY Mode"
            echo "=========================================="
            echo ""
            echo "Options:"
            echo "  1) Sync TO secondary"
            echo "  2) Show configuration differences"
            echo "  3) Exit"
            echo ""
            read -p "Choose option [1-3]: " choice
            
            case $choice in
                1) sync_to_secondary ;;
                2) show_diff ;;
                3) exit 0 ;;
                *) log_error "Invalid choice"; exit 1 ;;
            esac
        fi
        ;;
        
    backup|secondary)
        log_info "Running as SECONDARY node"
        
        if [ "$1" == "--diff" ]; then
            show_diff
        elif [ "$1" == "--auto" ]; then
            log_info "Auto-sync mode enabled"
            sync_from_primary
        else
            echo ""
            echo "Pi-hole Configuration Sync - SECONDARY Mode"
            echo "============================================"
            echo ""
            echo "Options:"
            echo "  1) Sync FROM primary"
            echo "  2) Show configuration differences"
            echo "  3) Exit"
            echo ""
            read -p "Choose option [1-3]: " choice
            
            case $choice in
                1) sync_from_primary ;;
                2) show_diff ;;
                3) exit 0 ;;
                *) log_error "Invalid choice"; exit 1 ;;
            esac
        fi
        ;;
        
    *)
        log_error "Unknown node type: $NODE_TYPE"
        log_error "Please run with: $0 [primary|secondary]"
        exit 1
        ;;
esac

log_info "Done!"
