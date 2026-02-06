FROM python:3.13-slim

LABEL description="Mock Pi-hole v6 API server for testing Pi-hole Sentinel"

WORKDIR /app
COPY mock_pihole.py .

# Install iproute2 for ARP/network testing compatibility
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 curl \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 80

HEALTHCHECK --interval=5s --timeout=2s --retries=3 --start-period=3s \
    CMD curl -sf http://localhost/api/version || exit 1

CMD ["python3", "-u", "mock_pihole.py"]
