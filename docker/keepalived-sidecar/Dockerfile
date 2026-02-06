FROM alpine:latest

# Install keepalived and dependencies
RUN apk add --no-cache \
    keepalived \
    bash \
    curl \
    iproute2 \
    gettext \
    jq

# Create required directories
RUN mkdir -p /etc/keepalived /scripts

# Copy configuration template and scripts
COPY keepalived.conf.tpl /etc/keepalived/keepalived.conf.tpl
COPY start.sh /scripts/start.sh
COPY check_health.sh /scripts/check_health.sh

# Make scripts executable
RUN chmod +x /scripts/*.sh

# Default environment variables
ENV KEEPALIVED_STATE="BACKUP" \
    KEEPALIVED_PRIORITY="100" \
    KEEPALIVED_INTERFACE="eth0" \
    KEEPALIVED_ROUTER_ID="51" \
    KEEPALIVED_AUTH_PASS="pihole_sentinel" \
    VIP_IP=""

# Entrypoint
ENTRYPOINT ["/scripts/start.sh"]
