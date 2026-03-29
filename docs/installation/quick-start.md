# Pi-hole Sentinel - Quick Start Guide

## Prerequisites

Before you begin, make sure you have:

- 2 working Pi-holes (Pi-hole v6.0+, Debian/Ubuntu)
- SSH root access to all servers
- Pi-hole web interface passwords
- A free IP address for the VIP (Virtual IP)
- (Optional) A separate monitor server

---

## Installation

### Step 1: Download Pi-hole Sentinel

On your **local machine** or **monitor server**:

```bash
# From a release
curl -sL https://api.github.com/repos/JBakers/pihole-sentinel/releases \
  | grep -m1 tarball_url | cut -d'"' -f4 | xargs curl -sL -o pihole-sentinel.tar.gz
tar xzf pihole-sentinel.tar.gz
mv JBakers-pihole-sentinel-* pihole-sentinel
cd pihole-sentinel/
```

Or clone the repository directly:

```bash
git clone https://github.com/JBakers/pihole-sentinel.git
cd pihole-sentinel/
```

### Step 2: Run Setup Script

```bash
sudo python3 setup.py
```

The script will interactively ask for:

#### Network Configuration
```
Network interface name [eth0]: eth0
Primary Pi-hole IP: 10.10.100.10
Secondary Pi-hole IP: 10.10.100.20
Virtual IP (VIP): 10.10.100.2
Network gateway IP: 10.10.100.1
```

#### DHCP Configuration
```
Do you use DHCP on Pi-holes? [y/N]: y
```

#### Monitor Server
```
Run monitor on separate server? [y/N]: y
Monitor server IP: 10.10.100.30
```

#### SSH & Passwords (one-time)
```
SSH user [root]: root
SSH port [22]: 22
SSH password for root@10.10.100.10: ********
SSH password for root@10.10.100.20: ********
SSH password for root@10.10.100.30: ********
Primary Pi-hole web password: ********
Secondary Pi-hole web password: ********
```

### Step 3: Deploy

Select the deployment option:

```
Select deployment option:
1) Generate configs only
2) Generate and deploy to all servers via SSH [RECOMMENDED]
3) Deploy to monitor server only
4) Deploy to primary Pi-hole only
5) Deploy to secondary Pi-hole only

Choice [2]: 2
```

The setup script will **automatically**:
- Generate and distribute SSH keys
- Install dependencies on all servers
- Configure keepalived on both Pi-holes
- Deploy the monitor service with dashboard
- Generate and inject an API key
- Start all services
- Configure timezone and NTP
- Clean up sensitive files

**Wait until you see:**
```
┌─────────────────────────────────────────────────────┐
│         DEPLOYMENT COMPLETED SUCCESSFULLY!           │
└─────────────────────────────────────────────────────┘

All services deployed and started successfully!
You can now access the dashboard at: http://10.10.100.30:8080
```

**That's it.** No manual API key configuration is needed — setup.py handles everything.

---

## Verification

### Check Services

```bash
# Monitor service
ssh root@10.10.100.30 systemctl status pihole-monitor

# Keepalived on both Pi-holes
ssh root@10.10.100.10 systemctl status keepalived
ssh root@10.10.100.20 systemctl status keepalived
```

All services should show **active (running)**.

### Open Dashboard

Open in your browser: `http://10.10.100.30:8080`

The dashboard shows real-time status of both Pi-holes, VIP location, DHCP status, and event history.

### VIP Check

```bash
# Check which Pi-hole has the VIP
ssh root@10.10.100.10 "ip addr show | grep 10.10.100.2"
ssh root@10.10.100.20 "ip addr show | grep 10.10.100.2"
```

The VIP should be visible on exactly one Pi-hole (the MASTER).

### Failover Test

```bash
# Stop FTL on the MASTER (the one with VIP)
ssh root@10.10.100.10 systemctl stop pihole-FTL

# Watch the dashboard — within ~30 seconds:
# - Secondary becomes MASTER
# - VIP moves to secondary
# - DHCP moves to secondary (if enabled)

# Restore
ssh root@10.10.100.10 systemctl start pihole-FTL

# Primary should preempt back to MASTER within ~30 seconds
```

---

## What You Get

### High Availability
- Automatic failover (< 30 seconds)
- DHCP failover (when enabled)
- Automatic failback
- VIP management via keepalived (VRRP)

### Monitoring
- Real-time status polling every 10 seconds
- Automatic VIP detection (ARP-based)
- Historical data and graphs
- Event logging and timeline

### Notifications
- Telegram, Discord, Pushover, Ntfy, custom webhooks
- Configurable per event type (failover, recovery, fault)
- Fault debounce and paired recovery notifications
- Snooze support

### Security
- API key authentication on all endpoints
- CORS restricted
- No credential exposure
- Passwords stored as environment variables
- Rate limiting on test endpoints

---

## Important Endpoints

### Dashboard
- **Main Dashboard:** `http://<monitor-ip>:8080`
- **Settings:** `http://<monitor-ip>:8080/settings.html`

### API (with `X-API-Key` header)

| Endpoint | Description |
|----------|-------------|
| `GET /api/status` | Real-time system status |
| `GET /api/history?hours=24` | Historical data |
| `GET /api/events?limit=50` | Event timeline |
| `GET /api/version` | Current version |
| `GET /api/check-update` | Check for updates |
| `POST /api/commands/{name}` | Run system commands |
| `GET/POST /api/notifications/settings` | Notification config |

See **[API Documentation](../api/README.md)** for full details.

---

## Troubleshooting

### "Connection refused" to monitor

```bash
ssh root@10.10.100.30 systemctl status pihole-monitor
ssh root@10.10.100.30 journalctl -u pihole-monitor -n 50

# Restart if needed
ssh root@10.10.100.30 systemctl restart pihole-monitor
```

### Failover not working

```bash
# Check keepalived on both nodes
ssh root@10.10.100.10 systemctl status keepalived
ssh root@10.10.100.20 systemctl status keepalived

# Check VRRP traffic
ssh root@10.10.100.10 'tcpdump -n -i any vrrp | head -20'

# Both must have the same virtual_router_id
ssh root@10.10.100.10 grep virtual_router_id /etc/keepalived/keepalived.conf
ssh root@10.10.100.20 grep virtual_router_id /etc/keepalived/keepalived.conf
```

### DHCP not switching during failover

Check the keepalived notify log:
```bash
ssh root@10.10.100.20 tail -20 /var/log/keepalived-notify.log
```

If you see "port 67 not yet bound", the DHCP control script will automatically
restart FTL as a fallback. Verify port 67 status:
```bash
ssh root@10.10.100.20 ss -ulnp | grep :67
```

---

## More Information

- **[Existing Setup Guide](existing-setup.md)** — Add HA to existing Pi-holes manually
- **[Configuration Sync](../maintenance/sync.md)** — Keep Pi-holes synchronized
- **[CLI Tool](../usage/cli-tool.md)** — `pisen` command-line utility
- **[API Documentation](../api/README.md)** — Full API reference
- **[Testing Guide](../development/testing.md)** — Test procedures
