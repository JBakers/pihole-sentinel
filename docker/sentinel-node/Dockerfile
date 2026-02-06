FROM alpine:3.21

LABEL maintainer="JBakers" \
    description="Pi-hole Sentinel Node - Keepalived + Sync Agent sidecar"

# ── System packages ─────────────────────────────────────────
RUN apk add --no-cache \
    keepalived \
    python3 \
    py3-pip \
    bash \
    curl \
    iproute2 \
    gettext \
    jq

# ── Python dependencies (sync agent) ───────────────────────
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# ── Create directories ──────────────────────────────────────
RUN mkdir -p /etc/keepalived /scripts /data /app

# ── Copy keepalived config and scripts ──────────────────────
COPY keepalived/keepalived.conf.tpl /etc/keepalived/keepalived.conf.tpl
COPY keepalived/start_keepalived.sh /scripts/start_keepalived.sh
COPY keepalived/check_health.sh /scripts/check_health.sh
COPY keepalived/notify.sh /scripts/notify.sh

# ── Copy sync agent ─────────────────────────────────────────
COPY sync_agent/ /app/

# ── Copy entrypoint ─────────────────────────────────────────
COPY entrypoint.sh /scripts/entrypoint.sh

# Make all scripts executable
RUN chmod +x /scripts/*.sh

# ── Ports ───────────────────────────────────────────────────
# 5000 = Sync Agent API
EXPOSE 5000

# ── Default environment ─────────────────────────────────────
ENV KEEPALIVED_STATE="BACKUP" \
    KEEPALIVED_PRIORITY="100" \
    KEEPALIVED_INTERFACE="eth0" \
    KEEPALIVED_ROUTER_ID="51" \
    KEEPALIVED_AUTH_PASS="changeme" \
    VIP_IP="" \
    PIHOLE_HOST="127.0.0.1" \
    PIHOLE_WEB_PORT="80" \
    PIHOLE_DNS_PORT="53" \
    PIHOLE_PASSWORD="" \
    SYNC_TOKEN="" \
    SYNC_PEERS="" \
    NODE_NAME="" \
    NODE_ROLE="backup"

ENTRYPOINT ["/scripts/entrypoint.sh"]
