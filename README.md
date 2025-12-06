<div align="center">

<img src="logo.svg" alt="Pi-hole Sentinel Logo" width="200"/>

# Pi-hole Sentinel

resilient dns · simple ops · keep dns up when others drop

**High Availability for Pi-hole**

*Automatic failover • Real-time monitoring • Quick IP flow + monitor placement guidance • Seamless DNS/DHCP redundancy*

[![Version](https://img.shields.io/badge/version-v0.10.0--beta.20-blue.svg)](VERSION)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub Issues](https://img.shields.io/github/issues/JBakers/pihole-sentinel)](https://github.com/JBakers/pihole-sentinel/issues)
[![GitHub Stars](https://img.shields.io/github/stars/JBakers/pihole-sentinel)](https://github.com/JBakers/pihole-sentinel/stargazers)
[![Made by JBakers](https://img.shields.io/badge/Made%20by-JBakers-667eea)](https://github.com/JBakers)

[Features](#what-does-it-do) • [Installation](#installation) • [Notifications](#notifications) • [Documentation](#setup-options)

</div>

---

## Introduction

Pi-hole Sentinel brings enterprise-grade high availability to your Pi-hole DNS infrastructure. If you rely on Pi-hole for network-wide ad blocking and DNS filtering, you know the frustration when your Pi-hole goes down - suddenly your entire network loses DNS resolution.

Pi-hole Sentinel solves this with automatic failover using a Virtual IP (VIP) that seamlessly switches between your primary and backup Pi-hole servers. When your primary Pi-hole fails, the backup takes over instantly without any manual intervention or DNS changes on your devices. Optional DHCP failover ensures uninterrupted network services.

Built for home networks and small businesses that need reliability without complexity. Works with your existing Pi-hole setup - no special configuration required.

## What does it do?

1. **Automatic Failover** 
   - Virtual IP (VIP) that switches automatically
   - Seamless DNS service during outages
   - Optional DHCP failover with automatic activation/deactivation
   - DHCP misconfiguration detection and warnings
   - Compatible with existing sync solutions (Nebula-sync, etc.)

2. **Real-time Monitoring**
   - Beautiful web dashboard with live updates
   - Real-time status indicators for all services
   - Server connectivity monitoring via TCP
   - DNS resolution testing
   - DHCP server status monitoring
   - VIP detection via MAC address comparison
   - Failover/failback detection and logging
   - Historical data and event timeline
   - Works on desktop and mobile
   - Dark mode support

3. **Smart Notifications**
   - Web-based configuration interface
   - Multiple notification services supported
   - Test notifications before saving
   - Alerts for state changes (MASTER/BACKUP/FAULT)
   - DHCP misconfiguration warnings

## Setup Options

### Features
- **DNS Failover**: Always enabled
- **DHCP Failover**: Optional, if you use DHCP on your Pi-holes
- **Configuration Sync**: Built-in sync script (includes DHCP leases)
- **Monitoring**: Choose between separate server or on primary Pi-hole
- **Notifications**: Web-based setup for Telegram, Discord, Pushover, Ntfy, and webhooks
- **Compatible**: Works alongside existing sync solutions (Nebula-sync, etc.)

### Prerequisites
- ✅ 2 working Pi-holes (with DNS)
- ✅ SSH root access to all servers (passwords asked once for SSH key setup)
- ✅ Pi-hole web interface passwords
- ✅ Separate server for monitoring (recommended, or install on primary)

### Required Information
- 📝 Primary Pi-hole IP
- 📝 Secondary Pi-hole IP
- 📝 Free IP for VIP (Virtual IP)
- 📝 Router/gateway IP
- 📝 Network interface name (usually eth0 or ens18)
- 📝 DHCP status (if you want failover)
- 📝 SSH user and port (defaults: root, 22)
- 📝 SSH passwords (asked once to setup passwordless access)

## Components

### Pi-hole Servers
- Keepalived (automatic installation)
  - Manages VIP failover
  - Monitors Pi-hole service
  - Handles DHCP failover (if enabled)
- arping (automatic installation)
  - Network connectivity checks
  - ARP table updates

### Monitor Server
- Python 3.8+ (required packages auto-installed)
- Web dashboard
  - Real-time status monitoring
  - Failover history
  - Service health checks

## System Requirements

### Pi-hole Servers
- Pi-hole v6.0 or newer (2024+)
- Debian/Ubuntu based system
- Root/sudo access
- Static IP addresses
- No special Pi-hole settings needed
- Works with existing configuration

**System Packages (auto-installed by setup.py):**
- `build-essential` - Compiler toolchain for Python packages
- `python3.11-dev` - Python 3.11 development headers (required for C extensions)
- `python3-pip` - Python package manager (pip)
- `iproute2` - Network configuration utilities
- `iputils-ping` - Ping command for connectivity checks
- `dnsutils` - DNS testing utilities (dig command)
- `arping` - ARP ping utility
- `keepalived` - VRRP implementation for failover
- `sqlite3` - Database for monitoring
- `python3.11-venv` - Python virtual environment support
- `sshpass` - SSH password authentication utility (for remote deployment)

**Note:** Setup script automatically detects and configures timezone from your system using `timedatectl`, with fallback to Europe/Amsterdam if detection fails. NTP synchronization is also configured automatically.

### Monitor Server
- Any Linux system (Debian/Ubuntu recommended)
- Root/sudo access
- 512MB RAM minimum
- 1GB free disk space
- Network access to both Pi-holes
- Python 3.8+ available

**Python Packages (auto-installed by setup.py):**
- `fastapi` - Web framework for monitoring API
- `uvicorn` - ASGI server
- `aiohttp` - Async HTTP client for Pi-hole communication
- `aiosqlite` - Async SQLite database
- `aiofiles` - Async file operations
- `python-dotenv` - Environment variable management
- `python-dateutil` - Date/time utilities
- `setuptools` - Python package development tools
- `wheel` - Python package build tool

## Quick Start

- Clone and enter the repo: `git clone https://github.com/JBakers/pihole-sentinel.git && cd pihole-sentinel`
- Run the wizard: `sudo python3 setup.py`
- Choose the quick IP flow and confirm where the monitor should run
- Pick option 1 (generate configs to copy manually) or option 2 (deploy everything via SSH)
- Configure notifications at `http://<monitor-ip>:8080/settings.html`
- **Security:** `generated_configs/` contains secrets after setup—remove it once you deploy

## Installation

> **✨ NEW:** Fully automated setup with SSH key generation!
> 
> **Simple setup:** Run setup.py once on ANY machine with network access to your servers.
> No manual SSH key setup required - everything is automated!

### Quick Installation (Recommended)

**One-Command Automated Setup:**

```bash
git clone https://github.com/JBakers/pihole-sentinel.git
cd pihole-sentinel
sudo python3 setup.py
```

The setup script will:
1. ✅ Check and install system dependencies
2. ✅ Ask for your network configuration (IPs, VIP, gateway, etc.)
3. ✅ Ask for DHCP configuration (if enabled)
4. ✅ Ask for SSH details (user and port - same for all servers)
5. ✅ Ask for SSH passwords (once, to distribute keys)
6. ✅ **Automatically generate SSH keys** (~/.ssh/id_pihole_sentinel)
7. ✅ **Distribute keys to all servers** (passwordless access!)
8. ✅ Generate secure passwords for keepalived
9. ✅ Create all configuration files
10. ✅ **Automatically inject Pi-hole API keys into dashboard** (v0.9.0+)
11. ✅ **Deploy to all servers via SSH** (choose option 2)
12. ✅ Auto-detect and configure timezone with NTP on all servers
13. ✅ **Securely cleanup sensitive files** after deployment

**Features:**
- 🔐 Automatic SSH key generation and distribution
- 🚀 One-click deployment to all servers
- 🔑 Automatic API key injection into dashboard (v0.9.0+)
- 🔒 Automatic cleanup of sensitive configuration files
- 🎨 Beautiful colored output with ASCII art logo
- 📊 Progress indicators for all operations
- ⏰ Automatic timezone detection from system (with fallback support)
- 🔍 Verbose mode available (--verbose flag)

**No Prerequisites Needed:**
- ❌ No manual SSH key setup required
- ❌ No sshpass needed (keys are automatically distributed)
- ✅ Just SSH password access to your servers

### Alternative: Manual Deployment

If you prefer not to use SSH deployment:

**Option 1: Generate configs, deploy manually**
```bash
sudo python3 setup.py
# Choose option 1, then copy files to each server manually
```

**Option 2: Run setup on each server individually**
- Clone repo on each server
- Run setup.py with option 3, 4, or 5 on respective servers

### What the Setup Does

The automated setup script will:
   - ✅ Check and install all system dependencies (with your approval)
   - ✅ Collect network configuration interactively
   - ✅ Validate all IP addresses and network settings
   - ✅ Generate SSH keys automatically
   - ✅ Distribute SSH keys to all servers
   - ✅ Generate secure random passwords for keepalived
   - ✅ Create all configuration files
   - ✅ Deploy monitor service (FastAPI + SQLite database)
   - ✅ Deploy keepalived on both Pi-holes
   - ✅ Auto-detect and configure timezone with NTP synchronization
   - ✅ Set proper file permissions (600 for .env files)
   - ✅ Enable and start all services
   - ✅ Securely cleanup sensitive files from local machine
   - ✅ Show helpful commands for verification

### Security Features

🔒 **Automatic Security Measures:**
- SSH passwords are cleared from memory after key distribution
- Generated config files are overwritten with random data before deletion
- Automatic cleanup on success, error, or keyboard interrupt
- SSH keys use ed25519 encryption
- Configuration files on servers have proper permissions (chmod 600)
- No sensitive data remains on the machine that ran setup

### Dashboard Features

📊 **Real-time Monitoring Dashboard:**
- Live status indicators (Server Online, Pi-hole Service, Virtual IP, DNS, DHCP)
- Color-coded states: Green for MASTER, Red for BACKUP
- Equal-thickness borders (4px) for clear visual distinction
- Descriptive status labels with hover tooltips
- DHCP misconfiguration detection with warning indicators
- Dark mode support with enhanced glows
- Node IP addresses displayed on cards
- Historical graphs with 1h/6h/24h/7d/30d time ranges
- Event timeline with detailed failover history
- Collapsible sections for better organization
- Responsive design for mobile and desktop

### Verification

**After Deployment, the setup shows helpful commands:**

1. **Access Monitor Dashboard**
   ```bash
   # Open in browser
   http://<monitor-ip>:8080
   ```

2. **Check Services**
   ```bash
   # On monitor server
   systemctl status pihole-monitor
   journalctl -u pihole-monitor -f
   
   # On both Pi-holes
   systemctl status keepalived
   systemctl status pihole-FTL
   
   # Check which server has the VIP
   ip addr show | grep <vip-address>
   ```

3. **Test Failover**
   ```bash
   # On the MASTER server (the one with VIP)
   systemctl stop pihole-FTL
   
   # Watch VIP move to BACKUP server
   # Check dashboard for status changes
   
   # Restore service
   systemctl start pihole-FTL
   ```

4. **Configure Notifications (Optional)**
   - Open settings: `http://<monitor-ip>:8080/settings.html`
   - Enable and configure your preferred notification service
   - Test notifications before saving
   - Supported: Telegram, Discord, Pushover, Ntfy, Custom Webhooks

### Monitoring Features

**Real-time Status Checks:**
- ✅ **Server Online** - TCP connectivity test (port 80)
- ✅ **Pi-hole Service** - FTL daemon status via API
- ✅ **Virtual IP Active** - MAC address comparison via ARP table
- ✅ **DNS Resolver** - Actual DNS query test (dig)
- ✅ **DHCP Server** - Configuration status via /api/config/dhcp
- ⚠️ **DHCP Misconfiguration** - Warns if MASTER has DHCP off or BACKUP has DHCP on

**Technical Details:**
- Connectivity: TCP socket tests instead of ICMP ping (no special capabilities needed)
- VIP Detection: Creates TCP connections to populate ARP table, then compares MAC addresses
- DHCP Monitoring: Uses `/api/config/dhcp` endpoint for accurate status
- Database: SQLite with history tracking (primary_dhcp, secondary_dhcp columns)
- Update Interval: 10 seconds (configurable via .env)

Follow the Quick Start steps above for the full setup flow.

## Management

### Daily Operations
- Monitor dashboard: `http://<monitor-ip>:8080`
- Notification settings: `http://<monitor-ip>:8080/settings.html`
- Check VIP status: `ping <vip-address>`
- View Keepalived status: `systemctl status keepalived`

### Logs
- **Monitor logs:** `journalctl -u pihole-monitor -f` or `/var/log/pihole-monitor.log`
- **Keepalived events:** `/var/log/keepalived-notify.log`
- **System logs:** `journalctl -u keepalived`

### Troubleshooting
- **Monitor issues:**
  - Check service: `systemctl status pihole-monitor`
  - View logs: `journalctl -u pihole-monitor -f`
  - Check connectivity: `curl http://<pihole-ip>/api/stats/summary`

- **Keepalived issues:**
  - Check config: `keepalived -t -f /etc/keepalived/keepalived.conf`
  - View VRRP traffic: `tcpdump -n -i any vrrp`
  - Check VIP assignment: `ip addr show | grep <vip>`

- **Sync issues:**
  - Test SSH: `ssh root@<other-pihole> echo OK`
  - Manual sync: `/usr/local/bin/sync-pihole-config.sh`
  - Check logs in sync output

### Upgrading

**Upgrading to latest version:**

Follow these steps to upgrade your installation:

1. **Backup your current setup:**
   ```bash
   # On monitor server
   sudo systemctl stop pihole-monitor
   sudo cp -r /opt/pihole-monitor /opt/pihole-monitor.backup
   ```

2. **Pull latest code:**
   ```bash
   cd pihole-sentinel
   git pull origin main
   ```

3. **Update dependencies on monitor server:**
   ```bash
   # Via SSH or directly on monitor
   cd /opt/pihole-monitor
   source venv/bin/activate
   pip install --upgrade -r /path/to/pihole-sentinel/requirements.txt
   deactivate
   ```

4. **Update monitor.py:**
   ```bash
   sudo cp /path/to/pihole-sentinel/dashboard/monitor.py /opt/pihole-monitor/monitor.py
   sudo chown pihole-monitor:pihole-monitor /opt/pihole-monitor/monitor.py
   ```

5. **Restart services:**
   ```bash
   sudo systemctl restart pihole-monitor
   ```

6. **Verify:**
   ```bash
   sudo systemctl status pihole-monitor
   sudo tail -f /var/log/pihole-monitor.log
   ```

**Notes:**
- Configuration files (.env) remain compatible across versions
- Keepalived configs are backward compatible
- Check CHANGELOG.md for version-specific changes

### Maintenance
- Check for updates: `git pull origin main` and review `CHANGELOG.md`
- Update Pi-hole normally - failover handles it automatically
- Keep system packages updated: `apt update && apt upgrade`
- Review logs weekly for any warnings or errors

## Monitoring & Maintenance

### Monitor Dashboard
- Access web interface: `http://<monitor-ip>:8080`
- View logs: `sudo journalctl -u pihole-monitor`
- Restart service: `sudo systemctl restart pihole-monitor`

### Keepalived Status
```bash
# Check service status
sudo systemctl status keepalived

# View logs
tail -f /var/log/keepalived-notify.log
tail -f /var/log/syslog | grep keepalived

# Check VIP assignment
ip addr show
```

### Testing Failover
1. On master node:
```bash
sudo systemctl stop pihole-FTL
# Monitor dashboard for failover
```

2. On backup node:
```bash
# Verify VIP assignment
ip addr show
```

## Notifications

Pi-hole Sentinel can send notifications when failover events occur. Configure via the web interface:

### Setup Notifications

1. Open settings page: `http://<monitor-ip>:8080/settings.html`
2. Choose your notification service(s)
3. Fill in credentials/tokens
4. Click "Send Test Message" to verify
5. Save settings

### Supported Services

- **📱 Telegram**: Create a bot with [@BotFather](https://t.me/BotFather) and get your chat ID
- **💬 Discord**: Create a webhook in your channel settings
- **🔔 Pushover**: Sign up at [pushover.net](https://pushover.net/) and create an app
- **🔕 Ntfy**: Choose a topic at [ntfy.sh](https://ntfy.sh) or use your own server
- **🔗 Custom Webhook**: POST JSON to any endpoint

### What Gets Notified

- 🟢 **MASTER** - Node becomes active (VIP assigned, DHCP enabled)
- 🟡 **BACKUP** - Node goes to standby (DHCP disabled)
- 🔴 **FAULT** - Node has issues (service problems detected)

All notifications include timestamp, hostname, and status details.

## Technical Details

### Architecture

**Components:**
- **Keepalived (VRRP)** - Manages VIP failover between Pi-holes
- **Monitor Service** - FastAPI application with real-time monitoring
- **SQLite Database** - Stores status history and events
- **Health Check Scripts** - Monitors Pi-hole FTL and DHCP services

**Network Flow:**
1. Both Pi-holes run keepalived with VRRP protocol
2. MASTER holds VIP and enables DHCP (if configured)
3. Monitor polls both Pi-holes every 10 seconds
4. Health checks determine if services are running
5. Automatic failover on service failure
6. DHCP automatically disabled on BACKUP

### Monitoring Technology

**Connectivity Detection:**
- Uses TCP socket connection tests (port 80) instead of ICMP ping
- No special Linux capabilities (CAP_NET_RAW) required
- Faster and more reliable than ping in container environments

**VIP Detection Method:**
```
1. Create TCP connections to VIP and both servers
2. Wait for ARP table to populate (200ms)
3. Extract MAC addresses from 'ip neigh show'
4. Compare VIP MAC with both server MACs
5. Determine which server currently holds the VIP
```

**DHCP Monitoring:**
- Uses Pi-hole v6 API endpoint: `/api/config/dhcp`
- Parses `config.dhcp.active` boolean value
- Detects misconfigurations (MASTER without DHCP / BACKUP with DHCP)
- Automatic warnings and notifications

**Pi-hole v6 API Compatibility:**
- Fixed authentication to use `session.sid` path
- Proper handling of new API response structure
- Backward compatible error handling

### Database Schema

```sql
CREATE TABLE status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    primary_state TEXT,          -- MASTER or BACKUP
    secondary_state TEXT,        -- MASTER or BACKUP
    primary_has_vip BOOLEAN,     -- VIP detection
    secondary_has_vip BOOLEAN,   -- VIP detection
    primary_online BOOLEAN,      -- Connectivity
    secondary_online BOOLEAN,    -- Connectivity
    primary_pihole BOOLEAN,      -- FTL service
    secondary_pihole BOOLEAN,    -- FTL service
    primary_dns BOOLEAN,         -- DNS queries working
    secondary_dns BOOLEAN,       -- DNS queries working
    dhcp_leases INTEGER,         -- Active DHCP leases
    primary_dhcp BOOLEAN,        -- DHCP enabled
    secondary_dhcp BOOLEAN       -- DHCP enabled
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_timestamp,
    event_type TEXT,             -- info, warning, error, success
    message TEXT
);
```

### Configuration Files

**Generated by setup.py:**
- `primary_keepalived.conf` - Keepalived config for primary
- `secondary_keepalived.conf` - Keepalived config for secondary
- `monitor.env` - Monitor service environment variables
- `primary.env` - Primary Pi-hole environment variables
- `secondary.env` - Secondary Pi-hole environment variables

**Security Note:** All generated config files are automatically deleted after deployment (overwritten with random data first).

## Troubleshooting

### Monitor Issues
1. Check service status:
```bash
sudo systemctl status pihole-monitor
```

2. Verify connectivity:
```bash
ping <pihole-ip>
curl -X POST http://<pihole-ip>/api/auth
```

### Keepalived Issues
1. Check configuration:
```bash
sudo keepalived -t -f /etc/keepalived/keepalived.conf
```

2. Monitor VRRP messages:
```bash
sudo tcpdump -n -i any vrrp
```

### Notification Issues
1. Test notification from settings page
2. Check notification config: `/etc/pihole-sentinel/notify.conf`
3. Check keepalived logs: `tail -f /var/log/keepalived-notify.log`

## Security Considerations

**Automated Security Measures:**

1. **SSH Key Security**
   - Setup generates ed25519 SSH keys automatically
   - Keys stored in `~/.ssh/id_pihole_sentinel`
   - Passwords only used once to distribute keys
   - Passwords cleared from memory after use

2. **Configuration File Cleanup**
   - Generated configs contain Pi-hole passwords and keepalived secrets
   - Automatically overwritten with random data after deployment
   - Directory removed completely
   - Cleanup occurs on success, error, or keyboard interrupt

3. **Remote Server Security**
   - `.env` files have chmod 600 permissions (root only)
   - Keepalived configs have chmod 644 permissions
   - Scripts have chmod 755 permissions (executable)
   - Service runs as dedicated `pihole-monitor` user

4. **Best Practices**
   - Use strong Pi-hole web passwords
   - Keep systems updated
   - Monitor logs regularly
   - Use firewall rules to restrict access
   - Review notification settings regularly

**No Sensitive Data Left Behind:**
- ✅ SSH passwords cleared from memory
- ✅ Config files securely deleted
- ✅ Only SSH keys remain (standard Unix security)
- ✅ Remote configs have proper permissions

## Contributing

Feel free to submit issues and pull requests.

## License

MIT License - see LICENSE file for details
