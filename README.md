<div align="center">

<img src="logo.svg" alt="Pi-hole Sentinel Logo" width="200"/>

# Pi-hole Sentinel

**High Availability for Pi-hole**

*Automatic failover • Real-time monitoring • Seamless DNS/DHCP redundancy*

[![Version](https://img.shields.io/badge/version-0.1.0--alpha-orange.svg)](VERSION)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub Issues](https://img.shields.io/github/issues/JBakers/pihole-sentinel)](https://github.com/JBakers/pihole-sentinel/issues)
[![GitHub Stars](https://img.shields.io/github/stars/JBakers/pihole-sentinel)](https://github.com/JBakers/pihole-sentinel/stargazers)
[![Made by JBakers](https://img.shields.io/badge/Made%20by-JBakers-667eea)](https://github.com/JBakers)

[Features](#what-does-it-do) • [Installation](#installation) • [Notifications](#notifications) • [Documentation](#setup-options)

</div>

---

## What does it do?

1. **Automatic Failover** 
   - Virtual IP (VIP) that switches automatically
   - Seamless DNS service during outages
   - Optional DHCP failover support
   - Compatible with existing sync solutions (Nebula-sync, etc.)

2. **Real-time Monitoring**
   - Separate monitoring server
   - Web dashboard for both Pi-holes
   - Instant status and failover visibility
   - Works on desktop and mobile

3. **Smart Notifications**
   - Web-based configuration interface
   - Multiple notification services supported
   - Test notifications before saving
   - Alerts for state changes (MASTER/BACKUP/FAULT)

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
- ✅ SSH access to both Pi-holes
- ✅ Pi-hole web interface passwords
- ✅ Separate server for monitoring (recommended)

### Required Information
- 📝 Primary Pi-hole IP
- 📝 Secondary Pi-hole IP
- 📝 Free IP for VIP (Virtual IP)
- 📝 Router/gateway IP
- 📝 Network interface name (usually eth0)
- 📝 DHCP status (if you want failover)

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
- Pi-hole 2023.05 or newer
- Debian/Ubuntu based system
- Root/sudo access
- Static IP addresses
- No special Pi-hole settings needed
- Works with existing configuration

### Monitor Server
- Any Linux system (Debian/Ubuntu recommended)
- Root/sudo access
- 512MB RAM minimum
- 1GB free disk space
- Network access to both Pi-holes
- Python 3.8+ available

## Quick Start

- **📋 Existing Pi-holes**: See [`EXISTING-SETUP.md`](EXISTING-SETUP.md) for adding HA to your current setup
- **🔄 Configuration Sync**: See [`SYNC-SETUP.md`](SYNC-SETUP.md) for keeping Pi-holes in sync
- **🔔 Notifications**: Configure alerts via web interface at `http://monitor-ip:8080/settings.html`
- **⚙️ Automated Setup**: Use `setup.py` to generate all configurations automatically

## Installation

1. **Prepare Environment**
   ```bash
   git clone https://github.com/JBakers/pihole-sentinel.git
   cd pihole-sentinel
   ```

2. **Run Setup**
   ```bash
   python3 setup.py
   ```
   The setup will ask you about:
   - Network details
   - DHCP failover (if you want it)
   - Monitor server location
   - Pi-hole passwords

3. **Verify Installation**
   - Check Keepalived: `http://<VIP>/admin/`
   - Check Monitor: `http://<monitor-ip>:8080`

4. **Configure Notifications (Optional)**
   - Open settings: `http://<monitor-ip>:8080/settings.html`
   - Enable and configure your preferred notification service
   - Test notifications before saving
   - Supported: Telegram, Discord, Pushover, Ntfy, Custom Webhooks

See `EXISTING-SETUP.md` for detailed steps

## Management

### Daily Operations
- Monitor dashboard: `http://<monitor-ip>:8080`
- Notification settings: `http://<monitor-ip>:8080/settings.html`
- Check VIP status: `ping <vip-address>`
- View Keepalived status: `systemctl status keepalived`

### Troubleshooting
- Keepalived logs: `tail -f /var/log/keepalived-notify.log`
- Monitor logs: `journalctl -u pihole-monitor`
- Pi-hole service: `systemctl status pihole-FTL`

### Maintenance
- Updates available through your package manager
- No special steps needed when updating Pi-hole
- Failover automatically handles maintenance reboots

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

1. Change default passwords in .env files
2. Use secure authentication for Pi-hole APIs
3. Consider network isolation
4. Regular log monitoring
5. Keep systems updated

## Contributing

Feel free to submit issues and pull requests.

## License

MIT License - see LICENSE file for details

Deze repository bevat de volledige monitoring setup voor een high-availability Pi-hole configuratie.

## Structuur

```
monitoring/pihole-ha/
├── dashboard/          # Monitoring dashboard en service
│   ├── monitor.py     # FastAPI monitoring service
│   ├── index.html     # Web interface
│   └── service/       # Systemd service configuratie
│
└── keepalived/        # Keepalived configuratie
    ├── scripts/       # Gedeelde monitoring scripts
    ├── pihole1/      # Master Pi-hole configuratie
    └── pihole2/      # Backup Pi-hole configuratie
```

## Features

### Dashboard
- Real-time status monitoring
- Failover geschiedenis
- DHCP lease monitoring
- Dark/light mode interface
- Event logging

### Keepalived Setup
- Automatische failover
- Health checks
- DHCP service management
- Notificatie systeem

## Installatie

### Dashboard
1. Installeer de monitor service:
```bash
cd dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp service/pihole-monitor.service /etc/systemd/system/
systemctl enable --now pihole-monitor
```

### Keepalived
1. Installeer keepalived op beide Pi-holes:
```bash
apt install keepalived arping
```

2. Configureer Master (Pihole1):
```bash
cd keepalived/pihole1
cp .env.example .env
# Pas .env aan
./setup.sh
```

3. Configureer Backup (Pihole2):
```bash
cd keepalived/pihole2
cp .env.example .env
# Pas .env aan
./setup.sh
```

## Monitoring

- Dashboard: `http://<server-ip>:8080`
- Logs: 
  - `/var/log/keepalived-notify.log`
  - `/var/log/pihole-monitor.log`

## Onderhoud

- Start/stop monitoring: `systemctl [start|stop] pihole-monitor`
- Bekijk status: `systemctl status pihole-monitor`
- Controleer keepalived: `systemctl status keepalived`