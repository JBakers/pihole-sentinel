#!/bin/bash
set -e

echo "╔══════════════════════════════════════════════╗"
echo "║   Pi-hole Sentinel Node                      ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  Node:      ${NODE_NAME:-$(hostname)}"
echo "  Role:      ${NODE_ROLE}"
echo "  Pi-hole:   ${PIHOLE_HOST}:${PIHOLE_WEB_PORT}"
echo "  VIP:       ${VIP_IP}"
echo "  Peers:     ${SYNC_PEERS:-none}"
echo ""

# ── Validate ────────────────────────────────────────────────
if [ -z "$VIP_IP" ]; then
    echo "ERROR: VIP_IP is required"
    exit 1
fi

if [ -z "$SYNC_TOKEN" ]; then
    echo "WARNING: SYNC_TOKEN not set - sync API will be insecure!"
fi

# ── Start Keepalived (background) ──────────────────────────
echo "[1/2] Starting Keepalived..."
/scripts/start_keepalived.sh &
KEEPALIVED_PID=$!

# Give keepalived a moment to start
sleep 1

# ── Start Sync Agent (foreground) ──────────────────────────
echo "[2/2] Starting Sync Agent..."
exec python3 /app/agent.py
