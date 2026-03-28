<div align="center">

<img src="logo.svg" alt="Pi-hole Sentinel Logo" width="200"/>

# Pi-hole Sentinel

**High Availability for Pi-hole**

*Automatic failover • Real-time monitoring • Seamless DNS/DHCP redundancy*

[![Version](https://img.shields.io/badge/version-v0.12.1--beta.8-blue.svg)](VERSION)
[![License](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)
[![GitHub Issues](https://img.shields.io/github/issues/JBakers/pihole-sentinel)](https://github.com/JBakers/pihole-sentinel/issues)
[![GitHub Stars](https://img.shields.io/github/stars/JBakers/pihole-sentinel)](https://github.com/JBakers/pihole-sentinel/stargazers)
[![Made by JBakers](https://img.shields.io/badge/Made%20by-JBakers-667eea)](https://github.com/JBakers)

[Features](#features) • [Quick Start](#quick-start) • [Installation](#installation) • [Documentation](docs/README.md)

</div>

---

> [!WARNING]
> **🚧 ACTIVE DEVELOPMENT - BETA STATUS**
>
> Pi-hole Sentinel is currently in **active beta development** (v0.12.1-beta.8).
>
> While the codebase has passed quality audits (89/100 - Excellent) and is well-tested, it is **still in beta** and may receive breaking changes before the v1.0.0 stable release.
>
> **Recommended for:**
> - ✅ Home labs and testing environments
> - ✅ Tech enthusiasts who want to contribute feedback
> - ✅ Non-critical production environments (with testing first)
>
> **Not recommended for:**
> - ❌ Critical production environments without thorough testing
> - ❌ Users who need guaranteed stability
>
> **Your feedback and testing help make Pi-hole Sentinel production-ready!** Please [report any issues](https://github.com/JBakers/pihole-sentinel/issues) you encounter.

---

## Introduction

Pi-hole Sentinel brings enterprise-grade high availability to your Pi-hole DNS infrastructure. When your primary Pi-hole fails, the backup takes over instantly using a Virtual IP (VIP) that seamlessly switches between servers - no manual intervention, no DNS changes on your devices.

**Built for home networks and small businesses** that need reliability without complexity. Works with your existing Pi-hole setup - no special configuration required.

### Why Pi-hole Sentinel?

- 🚫 **No more network outages** when Pi-hole fails
- ⚡ **Instant automatic failover** (< 3 seconds)
- 📊 **Beautiful web dashboard** with real-time monitoring
- 🔔 **Smart notifications** via Telegram, Discord, Pushover, Ntfy, webhooks
- 🔧 **Simple setup** with automated deployment script
- 🔄 **Works with existing Pi-holes** - no reconfiguration needed

---

## Features

### 🔄 Automatic Failover
- **Virtual IP (VIP)** that switches automatically between Pi-holes
- **DNS failover** - always enabled, zero downtime
- **Optional DHCP failover** - automatic activation/deactivation
- **DHCP misconfiguration detection** - warns about split-brain scenarios
- **Compatible** with existing sync solutions (Nebula-sync, Gravity-sync, etc.)

### 📊 Real-time Monitoring
- **Live web dashboard** - desktop and mobile responsive
- **Service health checks** - connectivity, DNS resolution, DHCP status
- **VIP detection** - knows which Pi-hole has the VIP at all times
- **Historical data** - event timeline and failover history
- **Dark mode support** - easy on the eyes

### 🔔 Smart Notifications
- **Web-based configuration** - no config file editing
- **Multiple services** - Telegram, Discord, Pushover, Ntfy, custom webhooks
- **Event-based alerts** - failover, recovery, fault, startup
- **Test notifications** - verify before saving settings

---

## Quick Start

### Prerequisites

- ✅ **2 Pi-holes** - v6.0+, Debian/Ubuntu, static IPs
- ✅ **SSH root access** - passwords asked once for SSH key setup
- ✅ **Pi-hole passwords** - for web interface API access
- ✅ **Monitor server** - separate server recommended (or install on primary Pi-hole)
- ✅ **Free IP address** - for the Virtual IP (VIP)

### Installation

**1. Clone the repository:**

```bash
git clone https://github.com/JBakers/pihole-sentinel.git
cd pihole-sentinel
```

**2. Run the setup script:**

```bash
sudo python3 setup.py
```

**3. Follow the interactive wizard:**

The script will guide you through:
- Network configuration (IPs, VIP, interface name)
- DHCP failover setup (optional)
- SSH key generation and distribution
- Automated deployment to all servers
- Service startup and verification

**4. Access the dashboard:**

```
http://<monitor-ip>:8080
```

That's it! Your Pi-hole infrastructure now has automatic failover.

### What Gets Installed

**On Pi-hole servers:**
- Keepalived (VRRP failover daemon)
- Health check scripts (FTL monitoring, DHCP control)
- Notification scripts (state change alerts)

**On monitor server:**
- FastAPI monitoring service
- SQLite database (status history)
- Web dashboard (HTML/CSS/JS)

---

## Documentation

### 📚 [Complete Documentation](docs/README.md)

- **[Quick Start Guide](docs/installation/quick-start.md)** - Fast deployment with defaults
- **[Existing Pi-hole Setup](docs/installation/existing-setup.md)** - Add HA to existing Pi-holes
- **[Configuration Sync](docs/maintenance/sync.md)** - Keep Pi-holes synchronized
- **[Development Guide](docs/development/README.md)** - Setup dev environment
- **[Testing Guide](docs/development/testing.md)** - User testing procedures
- **[API Documentation](docs/api/README.md)** - REST API reference

### 📖 Additional Guides

- **[CLAUDE.md](CLAUDE.md)** - Comprehensive guide for AI assistants and advanced users
- **[CHANGELOG.md](CHANGELOG.md)** - Version history
- **[LICENSE](LICENSE)** - GPLv3 License

---

## System Requirements

### Pi-hole Servers
- **Pi-hole:** v6.0+ (2024+)
- **OS:** Debian 11+/Ubuntu 20.04+
- **Access:** Root/sudo
- **Network:** Static IP addresses
- **Compatibility:** Works with existing configuration

**Auto-installed packages:** `keepalived`, `arping`, `iproute2`, `dnsutils`, `build-essential`

### Monitor Server
- **OS:** Any Linux (Debian/Ubuntu recommended)
- **Python:** 3.8+ (tested with 3.11-3.13)
- **RAM:** 512MB minimum
- **Disk:** 1GB free space
- **Network:** Access to both Pi-holes

**Auto-installed packages:** Python packages via pip (`fastapi`, `uvicorn`, `aiohttp`, `aiosqlite`, etc.)

---

## Management

### Daily Operations

**Check monitor status:**
```bash
systemctl status pihole-monitor
journalctl -u pihole-monitor -f
```

**Check keepalived (on Pi-holes):**
```bash
systemctl status keepalived
tail -f /var/log/keepalived-notify.log
```

**Access dashboard:**
```
http://<monitor-ip>:8080
```

### Logs

**Monitor logs:**
```bash
journalctl -u pihole-monitor -f
```

**Keepalived logs (on Pi-holes):**
```bash
tail -f /var/log/keepalived-notify.log
journalctl -u keepalived -f
```

### Testing Failover

**Stop Pi-hole on current MASTER:**
```bash
systemctl stop pihole-FTL
```

**Monitor dashboard** will show:
- VIP moving to other server
- Failover event logged
- Notification sent (if configured)

**Start Pi-hole to restore:**
```bash
systemctl start pihole-FTL
```

### Upgrading

**On monitor server:**
```bash
cd /opt/pihole-monitor
git pull
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart pihole-monitor
```

**On Pi-hole servers:**
```bash
sudo systemctl restart keepalived
```

### Uninstalling

**Run the setup wizard and choose option 6:**
```bash
sudo python3 setup.py
# Choose: 6. Uninstall Pi-hole Sentinel from all servers
```

The uninstaller will:
- Ask for SSH access details (no Pi-hole passwords needed)
- Stop and disable `pihole-monitor` and `keepalived` on all servers
- Remove all Sentinel-managed files (`/opt/pihole-monitor`, keepalived configs, scripts)
- Leave Pi-hole itself completely untouched

---

## Notifications

### Setup

1. **Open dashboard:** `http://<monitor-ip>:8080`
2. **Click Settings** in navigation
3. **Configure services:**
   - Telegram: Bot token + Chat ID
   - Discord: Webhook URL
   - Pushover: User key + App token
   - Ntfy: Topic name (optional: custom server)
   - Webhook: Custom endpoint URL

4. **Test notifications** before saving
5. **Save settings**

### Supported Services

- **Telegram** - Bot API with HTML formatting
- **Discord** - Webhooks with rich embeds
- **Pushover** - Priority-based notifications
- **Ntfy** - Self-hosted or ntfy.sh
- **Custom Webhooks** - JSON POST to any endpoint

### Notification Events

- **Failover** - Secondary becomes MASTER (primary failed)
- **Recovery** - Primary becomes MASTER again (back online)
- **Fault** - Server entered FAULT state (service issues)
- **Startup** - Monitoring service started (optional, disabled by default)

---

## Architecture

```
┌──────────────┐         VIP           ┌──────────────┐
│  Primary     │◄─────(Keepalived)────►│  Secondary   │
│  Pi-hole     │                       │  Pi-hole     │
│              │      VRRP Protocol    │              │
│  + FTL       │                       │  + FTL       │
│  + Keepalived│                       │  + Keepalived│
└──────┬───────┘                       └───────┬──────┘
       │                                       │
       │            ┌──────────────┐           │
       └────────────►   Monitor    ◄───────────┘
                    │   Server     │
                    │              │
                    │  + FastAPI   │
                    │  + SQLite    │
                    │  + Dashboard │
                    └──────────────┘
```

### How It Works

1. **Keepalived (VRRP)** - Runs on both Pi-holes, manages VIP assignment
2. **Health Checks** - Monitors Pi-hole FTL service every 2 seconds
3. **Automatic Failover** - VIP moves to backup when primary fails (< 3s)
4. **Monitor Service** - Polls both Pi-holes every 10 seconds
5. **Web Dashboard** - Real-time status, history, notifications

---

## Troubleshooting

### Monitor Issues

**Service won't start:**
```bash
# Check logs
journalctl -u pihole-monitor -n 50

# Verify environment
cat /opt/pihole-monitor/.env

# Test manually
cd /opt/pihole-monitor
source venv/bin/activate
python monitor.py
```

**Dashboard not accessible:**
- Check firewall: `sudo ufw allow 8080/tcp`
- Verify service: `systemctl status pihole-monitor`
- Check binding: `ss -tlnp | grep 8080`

### Keepalived Issues

**VIP not assigned:**
```bash
# Check keepalived status
systemctl status keepalived
journalctl -u keepalived -n 50

# Check VIP
ip addr show | grep <VIP>

# Check VRRP state
tail -f /var/log/keepalived-notify.log
```

**Split-brain (both MASTER):**
- Check network connectivity between Pi-holes
- Verify interface name in `/etc/keepalived/keepalived.conf`
- Check firewall allows VRRP (protocol 112)

### Notification Issues

**Notifications not working:**
1. **Test in dashboard** - Settings → Test notification
2. **Check credentials** - Verify tokens/keys are correct
3. **Check logs** - `tail -f /var/log/keepalived-notify.log`
4. **Network access** - Ensure Pi-holes can reach notification services

---

## Security Considerations

- **API Keys** - Monitor dashboard protected by API key
- **Pi-hole Passwords** - Stored in `.env` files (chmod 600)
- **SSH Keys** - Ed25519 keys generated automatically
- **VRRP Auth** - Keepalived uses password authentication
- **File Permissions** - Secrets stored with restrictive permissions (600)
- **Network Security** - Deploy on trusted network (isolated VLAN recommended)

**Best Practices:**
- Use strong Pi-hole passwords (16+ characters)
- Restrict dashboard access (firewall rules)
- Regular system updates (`apt update && apt upgrade`)
- Monitor logs weekly
- Backup configurations

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

**See:** [CLAUDE.md - Contributing Changes](CLAUDE.md#contributing-changes) for detailed guidelines.

---

## License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)** - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **Pi-hole Team** - For the amazing DNS/ad-blocking software
- **Keepalived** - For robust VRRP implementation
- **Community** - For feedback, testing, and contributions

---

<div align="center">

**Made with ❤️ by [JBakers](https://github.com/JBakers)**

[⬆ Back to Top](#pi-hole-sentinel)

</div>
