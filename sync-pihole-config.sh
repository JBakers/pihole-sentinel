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

# Configuration - Update these with your IPs
PRIMARY_IP="${PRIMARY_IP:-192.168.1.10}"
SECONDARY_IP="${SECONDARY_IP:-192.168.1.11}"
PIHOLE_DIR="/etc/pihole"
BACKUP_DIR="/root/pihole-sync-backup"

# Determine node type
NODE_TYPE=""
if [ -f "/etc/keepalived/.env" ]; then
    source /etc/keepalived/.env
    NODE_TYPE="$NODE_STATE"
else
    echo -e "${YELLOW}Warning: Could not determine node type from /etc/keepalived/.env${NC}"
    echo "Please specify node type as argument: primary or secondary"
    NODE_TYPE="$1"
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
    
    # Keep only last 5 backups
    cd "$BACKUP_DIR"
    ls -t pihole-backup-*.tar.gz | tail -n +6 | xargs -r rm
    
    log_info "Backup created successfully"
}

sync_from_primary() {
    log_info "Syncing configuration FROM primary ($PRIMARY_IP)..."
    
    # Create backup before sync
    create_backup
    
    # Stop Pi-hole temporarily
    log_info "Stopping Pi-hole..."
    systemctl stop pihole-FTL
    
    # Sync gravity database (contains all lists, groups, clients, etc.)
    log_info "Syncing gravity database..."
    rsync -avz --progress "root@${PRIMARY_IP}:${PIHOLE_DIR}/gravity.db" "${PIHOLE_DIR}/" || {
        log_error "Failed to sync gravity.db"
        systemctl start pihole-FTL
        exit 1
    }
    
    # Sync custom DNS records
    log_info "Syncing custom DNS records..."
    rsync -avz --progress "root@${PRIMARY_IP}:${PIHOLE_DIR}/custom.list" "${PIHOLE_DIR}/" || {
        log_warn "Failed to sync custom.list (may not exist)"
    }
    
    # Sync CNAME records
    rsync -avz --progress "root@${PRIMARY_IP}:${PIHOLE_DIR}/05-pihole-custom-cname.conf" "${PIHOLE_DIR}/" 2>/dev/null || {
        log_warn "No custom CNAME records to sync"
    }
    
    # Sync DHCP static leases (maar niet dynamische leases)
    log_info "Syncing DHCP static leases..."
    if ssh "root@${PRIMARY_IP}" "[ -f ${PIHOLE_DIR}/dhcp.leases ]"; then
        rsync -avz --progress "root@${PRIMARY_IP}:${PIHOLE_DIR}/dhcp.leases" "${PIHOLE_DIR}/" || {
            log_warn "Failed to sync dhcp.leases"
        }
    fi
    
    # Sync Pi-hole configuration
    # DHCP config wordt gesynchroniseerd, maar 'active' state blijft lokaal
    log_info "Syncing Pi-hole configuration..."
    
    # Download remote pihole.toml
    rsync -avz --progress "root@${PRIMARY_IP}:${PIHOLE_DIR}/pihole.toml" "/tmp/pihole.toml.remote" || {
        log_warn "Failed to download pihole.toml"
    }
    
    # Behoud de lokale DHCP 'active' status
    if [ -f "/tmp/pihole.toml.remote" ] && [ -f "${PIHOLE_DIR}/pihole.toml" ]; then
        # Extract local DHCP active state
        local_dhcp_active=$(grep -A 5 '^\[dhcp\]' "${PIHOLE_DIR}/pihole.toml" | grep '^active = ' | head -n1)
        
        # Kopieer remote config
        cp "/tmp/pihole.toml.remote" "${PIHOLE_DIR}/pihole.toml"
        
        # Restore local DHCP active state als deze bestaat
        if [ -n "$local_dhcp_active" ]; then
            sed -i "/^\[dhcp\]/,/^\[/ s/^active = .*/$local_dhcp_active/" "${PIHOLE_DIR}/pihole.toml"
            log_info "Preserved local DHCP active state: $local_dhcp_active"
        fi
        
        rm -f "/tmp/pihole.toml.remote"
    fi
    
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
    
    # Ask secondary to create backup
    log_info "Creating backup on secondary..."
    ssh "root@${SECONDARY_IP}" "mkdir -p $BACKUP_DIR && \
        tar czf $BACKUP_DIR/pihole-backup-\$(date +%Y%m%d-%H%M%S).tar.gz \
        $PIHOLE_DIR/gravity.db $PIHOLE_DIR/custom.list $PIHOLE_DIR/pihole.toml 2>/dev/null || true"
    
    # Stop Pi-hole on secondary
    log_info "Stopping Pi-hole on secondary..."
    ssh "root@${SECONDARY_IP}" "systemctl stop pihole-FTL"
    
    # Push configuration files
    log_info "Pushing gravity database..."
    rsync -avz --progress "${PIHOLE_DIR}/gravity.db" "root@${SECONDARY_IP}:${PIHOLE_DIR}/" || {
        log_error "Failed to push gravity.db"
        ssh "root@${SECONDARY_IP}" "systemctl start pihole-FTL"
        exit 1
    }
    
    log_info "Pushing custom DNS records..."
    rsync -avz --progress "${PIHOLE_DIR}/custom.list" "root@${SECONDARY_IP}:${PIHOLE_DIR}/" 2>/dev/null || {
        log_warn "No custom.list to push"
    }
    
    rsync -avz --progress "${PIHOLE_DIR}/05-pihole-custom-cname.conf" "root@${SECONDARY_IP}:${PIHOLE_DIR}/" 2>/dev/null || {
        log_warn "No custom CNAME records to push"
    }
    
    # Push DHCP static leases
    log_info "Pushing DHCP static leases..."
    if [ -f "${PIHOLE_DIR}/dhcp.leases" ]; then
        rsync -avz --progress "${PIHOLE_DIR}/dhcp.leases" "root@${SECONDARY_IP}:${PIHOLE_DIR}/" || {
            log_warn "Failed to push dhcp.leases"
        }
    fi
    
    log_info "Pushing configuration..."
    
    # Get secondary's current DHCP active state
    secondary_dhcp_active=$(ssh "root@${SECONDARY_IP}" "grep -A 5 '^\[dhcp\]' ${PIHOLE_DIR}/pihole.toml | grep '^active = ' | head -n1" 2>/dev/null || echo "")
    
    # Push config
    rsync -avz --progress "${PIHOLE_DIR}/pihole.toml" "root@${SECONDARY_IP}:/tmp/pihole.toml.new"
    
    # Restore secondary's DHCP active state
    if [ -n "$secondary_dhcp_active" ]; then
        ssh "root@${SECONDARY_IP}" "sed -i \"/^\[dhcp\]/,/^\[/ s/^active = .*/$secondary_dhcp_active/\" /tmp/pihole.toml.new"
        log_info "Preserved secondary DHCP active state"
    fi
    
    # Move into place
    ssh "root@${SECONDARY_IP}" "mv /tmp/pihole.toml.new ${PIHOLE_DIR}/pihole.toml"
    
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
