#!/bin/bash
# Keepalived notify script - called on state transitions
# Arguments: $1 = GROUP|INSTANCE, $2 = name, $3 = MASTER|BACKUP|FAULT

TYPE=$1
NAME=$2
STATE=$3
TIMESTAMP=$(date -Iseconds)

echo "[NOTIFY] $TIMESTAMP - $TYPE $NAME -> $STATE"

# Write state to a file so the sync agent can read it
echo "{\"state\": \"$STATE\", \"timestamp\": \"$TIMESTAMP\", \"type\": \"$TYPE\", \"name\": \"$NAME\"}" > /data/keepalived_state.json

# Notify the sync agent via its local API
curl -sf -X POST "http://127.0.0.1:5000/internal/state-change" \
    -H "Content-Type: application/json" \
    -d "{\"state\": \"$STATE\", \"timestamp\": \"$TIMESTAMP\"}" \
    2>/dev/null || true
