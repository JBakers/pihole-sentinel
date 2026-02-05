# Local Development Setup

**For Local Development Use Only - Not Committed to Git**

---

## 📋 Overview

Pi-hole Sentinel repository contains only production-relevant code and documentation. Development and testing files are kept locally to keep the repository clean.

This guide shows how to set up these files in your local environment.

---

## 🐳 Docker Testing Environment

### Step 1: Create Dockerfile.dev

Create `Dockerfile.dev` in the repository root:

```dockerfile
# Dockerfile for Pi-hole Sentinel Development/Testing
# This is for local testing - NOT for production
# For production, use setup.py

FROM python:3.14-slim

LABEL maintainer="Pi-hole Sentinel"
LABEL description="Pi-hole Sentinel Monitor - Development Image"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    dnsmasq \
    keepalived \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-dev.txt

# Create data directory
RUN mkdir -p /data && chmod 755 /data

# Expose API port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/api/version || exit 1

# Default command - run monitor
CMD ["python3", "-u", "dashboard/monitor.py"]
```

### Step 2: Create docker-compose.test.yml

Create `docker-compose.test.yml` in the repository root:

```yaml
version: '3.8'

services:
  # Mock Pi-hole Primary (simulated via simple HTTP server)
  pihole-primary:
    image: python:3.14-slim
    container_name: sentinel-pihole-primary
    working_dir: /app
    command: >
      bash -c "
      apt-get update && apt-get install -y iproute2 dnsmasq &>/dev/null || true &&
      python3 -m http.server 80
      "
    environment:
      PYTHONUNBUFFERED: 1
    ports:
      - "8001:80"
    networks:
      test-net:
        ipv4_address: 172.20.0.10
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/admin/api.php"]
      interval: 5s
      timeout: 3s
      retries: 3
      start_period: 10s

  # Mock Pi-hole Secondary
  pihole-secondary:
    image: python:3.14-slim
    container_name: sentinel-pihole-secondary
    working_dir: /app
    command: >
      bash -c "
      apt-get update && apt-get install -y iproute2 dnsmasq &>/dev/null || true &&
      python3 -m http.server 80
      "
    environment:
      PYTHONUNBUFFERED: 1
    ports:
      - "8002:80"
    networks:
      test-net:
        ipv4_address: 172.20.0.11
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/admin/api.php"]
      interval: 5s
      timeout: 3s
      retries: 3
      start_period: 10s

  # Pi-hole Sentinel Monitor Service
  sentinel-monitor:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: sentinel-monitor
    environment:
      # Configuration
      PRIMARY_IP: pihole-primary
      PRIMARY_NAME: "Primary Pi-hole"
      PRIMARY_PASSWORD: testpass123
      SECONDARY_IP: pihole-secondary
      SECONDARY_NAME: "Secondary Pi-hole"
      SECONDARY_PASSWORD: testpass123
      VIP_ADDRESS: 172.20.0.100
      
      # Monitor settings
      CHECK_INTERVAL: 5
      DB_PATH: /data/monitor.db
      NOTIFY_CONFIG_PATH: /data/notify_settings.json
      API_KEY: test-api-key-12345
      
      # Logging
      LOG_LEVEL: DEBUG
      
    ports:
      - "8080:8080"
    
    volumes:
      - ./dashboard:/app/dashboard
      - ./setup.py:/app/setup.py
      - monitor-data:/data
    
    depends_on:
      pihole-primary:
        condition: service_healthy
      pihole-secondary:
        condition: service_healthy
    
    networks:
      - test-net
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/version"]
      interval: 5s
      timeout: 3s
      retries: 3
      start_period: 10s

  # Redis cache (optional - for future caching layer)
  redis:
    image: redis:7-alpine
    container_name: sentinel-redis
    ports:
      - "6379:6379"
    networks:
      - test-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3

volumes:
  monitor-data:
    driver: local

networks:
  test-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
```

### Step 3: Verify .gitignore Excludes These Files

Your `.gitignore` already excludes these files:
```
Dockerfile.dev
docker-compose.test.yml
tests/test_error_handling.py
```

These files won't be tracked by git.

---

## 🧪 Using Docker for Testing

### Start Development Environment

```bash
# Start all services
make docker-up

# Wait for services to be healthy
sleep 5

# View status
docker-compose -f docker-compose.test.yml ps
```

### Access Services

- **Monitor Dashboard:** http://localhost:8080/
- **Monitor API Swagger:** http://localhost:8080/api/docs
- **Primary Pi-hole Mock:** http://localhost:8001/
- **Secondary Pi-hole Mock:** http://localhost:8002/
- **Redis:** localhost:6379

### Run Tests

```bash
# Run all tests in Docker
make docker-test

# View logs
make docker-logs

# Run specific test
docker exec sentinel-monitor ./.github/scripts/run-syntax-checks.sh
```

### Stop Development Environment

```bash
# Stop and remove containers/volumes
make docker-down

# Or manually:
docker-compose -f docker-compose.test.yml down -v
```

---

## 🧪 Error Handling Test Framework

Create `tests/test_error_handling.py` for testing custom exceptions:

```python
"""
Tests for error handling in Pi-hole Sentinel.
"""

import pytest

class TestExceptionHierarchy:
    """Test custom exception classes."""
    
    def test_pihole_sentinel_exception_base(self):
        # exc = PiholeSentinelException("Test error", status_code=500)
        # assert exc.message == "Test error"
        # assert exc.status_code == 500
        pass
    
    def test_configuration_error_defaults_to_400(self):
        # exc = ConfigurationError("Invalid config")
        # assert exc.status_code == 400
        pass
    
    def test_authentication_error_defaults_to_403(self):
        # exc = AuthenticationError("Invalid API key")
        # assert exc.status_code == 403
        pass
    
    # ... additional test methods
```

This file is not tracked by git but provides a scaffold for testing.

---

## 📚 Local Testing Workflow

### Before Committing Code

```bash
# 1. Format code
make format

# 2. Run linters
make lint

# 3. Run tests
make test

# 4. Run full automated test suite
make run-all-tests

# Only commit if all pass
git add -A
git commit -m "feat: your changes"
```

### Using Docker for Isolated Testing

```bash
# 1. Start clean Docker environment
make docker-up

# 2. Run tests in Docker
make docker-test

# 3. View any failures
make docker-logs

# 4. Fix issues

# 5. Stop when done
make docker-down
```

---

## 📋 Files to Create Locally

| File | Purpose | Location | Tracked |
|------|---------|----------|---------|
| `Dockerfile.dev` | Development image | repo root | ❌ Local only |
| `docker-compose.test.yml` | Test environment | repo root | ❌ Local only |
| `tests/test_error_handling.py` | Exception tests | `tests/` | ❌ Local only |

---

## ✅ Verification

To verify your local setup:

```bash
# Check that files are not tracked
git status

# Should show nothing about these files (they're ignored)

# Check docker files exist locally
ls -la Dockerfile.dev docker-compose.test.yml

# Should show both files

# Verify they won't be committed
git ls-files | grep -E "(Dockerfile.dev|docker-compose.test)"

# Should show nothing (not tracked)
```

---

## 🚀 Development Commands

```bash
# Setup
make install-dev              # Install dev dependencies

# Testing
make test                     # Run all tests with coverage
make test-unit               # Unit tests only
make test-integration        # Integration tests
make test-cov                # Generate HTML coverage report
make test-fast               # Quick tests (no coverage)

# Code Quality
make lint                    # Run linters
make format                  # Auto-format code
make check-security          # Security checks

# Docker Testing
make docker-build            # Build dev image
make docker-up               # Start test environment
make docker-test             # Run tests in Docker
make docker-logs             # View container logs
make docker-down             # Stop test environment

# Automated Tests
make run-all-tests           # All automated test scripts
make run-syntax-checks       # Check Python/Bash syntax
make run-quality-checks      # Check code quality
make run-security-scans      # Security audit

# Cleanup
make clean                   # Remove generated files
```

---

## 📖 References

- **Testing Guide:** [docs/development/TESTING_WORKFLOW.md](docs/development/TESTING_WORKFLOW.md)
- **Coverage Plan:** [docs/development/TEST_COVERAGE_PLAN.md](docs/development/TEST_COVERAGE_PLAN.md)
- **Development Guide:** [docs/development/README.md](docs/development/README.md)
- **Makefile:** [Makefile](Makefile)

---

## 💡 Tips

1. **Keep files updated** - If upstream changes docker files, copy the latest versions here
2. **Use .gitignore** - Never commit these files by accident (they're ignored)
3. **Docker cleanup** - Run `make docker-down` to clean up containers and volumes
4. **Fresh builds** - Use `make docker-build` to rebuild image with latest code
5. **Debug mode** - Use `make docker-logs -f` to stream logs in real-time

---

**Last Updated:** 2025-12-07  
**Repository:** Production + Documentation  
**Local Setup:** This guide  
**Status:** ✅ Ready for development

