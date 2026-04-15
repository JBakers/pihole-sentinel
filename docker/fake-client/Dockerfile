FROM python:3.13-slim

LABEL description="Fake network client for Pi-hole Sentinel testing"

WORKDIR /app
COPY fake_client.py .

RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 iputils-ping curl \
    && rm -rf /var/lib/apt/lists/*

# NOTE: Test-only container. Running as root is acceptable for the
# local Docker test environment.
CMD ["python3", "-u", "fake_client.py"]
