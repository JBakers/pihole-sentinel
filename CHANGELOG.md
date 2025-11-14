# Changelog

All notable changes to Pi-hole Sentinel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-11-14

### 🔧 Improved

#### Dependencies
- **Updated Python dependencies to newer, more secure versions:**
  - `fastapi`: 0.68.0 → ≥0.104.0
  - `uvicorn`: 0.15.0 → ≥0.24.0 (with standard extras)
  - `aiohttp`: 3.8.1 → ≥3.9.0
  - `aiosqlite`: 0.17.0 → ≥0.19.0
  - `aiofiles`: 0.8.0 → ≥23.2.0
  - `python-dotenv`: 0.19.0 → ≥1.0.0
  - Added version constraints to root `requirements.txt`

#### Logging & Monitoring
- **Replaced all `print()` statements with proper logging in `monitor.py`:**
  - Added Python `logging` module with configurable levels
  - Logs now written to `/var/log/pihole-monitor.log` (when directory exists)
  - Better debugging with `logger.debug()`, `logger.info()`, `logger.warning()`, `logger.error()`
  - Added `exc_info=True` for better error traceability
  - Console output remains available via StreamHandler

#### Error Handling
- **Improved error handling in `sync-pihole-config.sh`:**
  - Now distinguishes between "file doesn't exist" vs "sync failed" errors
  - Checks if remote file exists before attempting rsync
  - Better error messages for network/permission issues
  - Exits with error on critical sync failures instead of continuing

#### VIP Detection
- **Added retry logic to VIP detection (`check_who_has_vip`):**
  - 3 retry attempts with 1-second delays between failures
  - Better logging of MAC address detection attempts
  - More reliable VIP detection in high-load scenarios
  - Clearer warnings when VIP has no ARP entry

#### Network Configuration
- **Fixed hardcoded network interface in keepalived scripts:**
  - `keepalived_notify.sh` now uses `${INTERFACE}` variable instead of hardcoded `eth0`
  - Reads interface from environment with fallback to `eth0`
  - Supports all network interface types (ens18, enp3s0, etc.)

#### Timezone Configuration
- **Made timezone auto-detection in `setup.py`:**
  - Automatically detects system timezone using `timedatectl`
  - Falls back to `Europe/Amsterdam` if detection fails
  - No longer hardcoded - adapts to system configuration
  - Better logging of configured timezone

### 🐛 Fixed
- Network interface no longer hardcoded in arping command
- VIP detection more reliable with retry mechanism
- Sync errors now properly reported instead of silently ignored
- DHCP configuration errors logged with correct severity
- All exceptions now properly logged with context

### 📚 Documentation
- Added this CHANGELOG.md file
- All changes documented with rationale

### 🔒 Security
- Updated dependencies address known CVEs in older versions
- Better error logging improves security incident detection
- No changes to existing security features

---

## [0.1.0] - 2025-11-13

### 🎉 Initial Release

#### Features
- **Automatic Failover**
  - Virtual IP (VIP) management with keepalived
  - Seamless DNS service during outages
  - Optional DHCP failover with automatic activation/deactivation
  - DHCP misconfiguration detection and warnings

- **Real-time Monitoring Dashboard**
  - Beautiful web interface with live updates
  - Real-time status indicators for all services
  - Historical data and event timeline
  - Dark mode support
  - Mobile responsive design

- **Smart Notifications**
  - Web-based configuration interface
  - Support for Telegram, Discord, Pushover, Ntfy, and custom webhooks
  - Test notifications before saving
  - Configurable event types

- **Automated Setup**
  - One-command installation with `setup.py`
  - Automatic SSH key generation and distribution
  - Remote deployment via SSH
  - Automatic dependency installation
  - Secure cleanup of sensitive files

- **Configuration Sync**
  - Built-in sync script for Pi-hole configurations
  - DHCP lease synchronization
  - Preserves local DHCP active state
  - Automatic backup before sync

#### Components
- FastAPI-based monitoring service
- SQLite database for history tracking
- Keepalived for VRRP failover
- Health check scripts for Pi-hole and DHCP
- Systemd service integration

#### Security
- SSH key-based authentication
- Automatic cleanup of generated configs
- Proper file permissions (600 for .env files)
- Password masking in web interface
- Secure random password generation

#### Documentation
- Comprehensive README.md
- Setup guide for existing Pi-holes (EXISTING-SETUP.md)
- Configuration sync documentation (SYNC-SETUP.md)
- MIT License

---

## Legend
- 🎉 New feature
- 🔧 Improvement/Enhancement
- 🐛 Bug fix
- 🔒 Security update
- 📚 Documentation
- ⚠️ Breaking change
- 🗑️ Deprecated/Removed
