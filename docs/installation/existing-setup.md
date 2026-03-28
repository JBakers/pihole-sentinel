# Pi-hole Sentinel - For Existing Pi-holes

## 🎯 For Users With Working Pi-holes

You already have working Pi-holes and want to add:
- ⚙️ Keepalived for automatic failover (Virtual IP)
- 📊 Monitor dashboard for real-time status
- 🔄 Built-in configuration sync (includes DHCP leases)

**This guide is for you if:**
- ✅ You have 2 working Pi-holes
- ✅ You optionally already have sync (Nebula-sync, Gravity-sync, etc.)
- ✅ You want to add HA without disrupting your existing setup

## 🚀 Quick Setup (30 minutes)

### Step 1: Download Pi-hole Sentinel (5 min)

```bash
wget -q $(curl -s https://api.github.com/repos/JBakers/pihole-sentinel/releases/latest \
  | grep -o 'https://.*pihole-sentinel-.*\.tar\.gz') -O pihole-sentinel.tar.gz
tar xzf pihole-sentinel.tar.gz
cd pihole-sentinel-*/
```

**Run setup script:**

```bash
python3 setup.py
```

**The script will ask for:**
```
Network interface (e.g., eth0, ens18)
Primary Pi-hole IP
Secondary Pi-hole IP
Virtual IP (VIP) - Choose a FREE IP in your network
Gateway IP (your router)
DHCP failover (y/n)
Monitor location (separate server or primary Pi-hole)
Pi-hole passwords (for API access)
```

**💡 Tips:**
- VIP must be an unused IP in the same subnet
- Use the web interface password of your Pi-holes
- Netmask is usually 24 for /24 networks

**Result:** All configuration files in `generated_configs/`

### Step 2: Deploy Keepalived on Primary (10 min)

```powershell
# Copy files
scp generated_configs/primary_keepalived.conf root@<primary-ip>:/tmp/
scp generated_configs/primary.env root@<primary-ip>:/tmp/
scp keepalived/scripts/*.sh root@<primary-ip>:/tmp/
```

**SSH to primary:**
```bash
ssh root@<primary-ip>

# Install keepalived (if not already installed)
apt update && apt install -y keepalived arping

# Deploy configuration
cp /tmp/primary_keepalived.conf /etc/keepalived/keepalived.conf
cp /tmp/primary.env /etc/keepalived/.env
cp /tmp/*.sh /usr/local/bin/
chmod +x /usr/local/bin/*.sh
chmod 644 /etc/keepalived/keepalived.conf
chmod 600 /etc/keepalived/.env
chown root:root /etc/keepalived/*

# Start keepalived
systemctl enable keepalived
systemctl start keepalived

# Check status
systemctl status keepalived

# Verify VIP is assigned
ip addr show | grep <your-vip>
```

### Step 3: Deploy Keepalived on Secondary (10 min)

```powershell
# Copy files
scp generated_configs/secondary_keepalived.conf root@<secondary-ip>:/tmp/
scp generated_configs/secondary.env root@<secondary-ip>:/tmp/
scp keepalived/scripts/*.sh root@<secondary-ip>:/tmp/
```

**SSH to secondary:**
```bash
ssh root@<secondary-ip>

apt update && apt install -y keepalived arping

cp /tmp/secondary_keepalived.conf /etc/keepalived/keepalived.conf
cp /tmp/secondary.env /etc/keepalived/.env
cp /tmp/*.sh /usr/local/bin/
chmod +x /usr/local/bin/*.sh
chmod 644 /etc/keepalived/keepalived.conf
chmod 600 /etc/keepalived/.env
chown root:root /etc/keepalived/*

systemctl enable keepalived
systemctl start keepalived
systemctl status keepalived

# VIP should NOT be visible (backup node)
ip addr show | grep <your-vip>
```

### Step 4: Deploy Monitor Dashboard (10 min)

```powershell
# Copy files to monitor
scp dashboard/monitor.py root@<monitor-ip>:/tmp/
scp dashboard/index.html root@<monitor-ip>:/tmp/
scp generated_configs/monitor.env root@<monitor-ip>:/tmp/
```

**SSH to monitor:**
```bash
ssh root@<monitor-ip>

# Install dependencies (if not already done)
apt update
apt install -y python3 python3-pip python3-venv

# Setup application
mkdir -p /opt/pihole-monitor
cd /opt/pihole-monitor

# Copy files
cp /tmp/monitor.py .
cp /tmp/index.html .
cp /tmp/monitor.env .env

# Python environment
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn aiohttp aiosqlite python-dotenv

# Create service user
useradd -r -s /bin/false pihole-monitor || true

# Permissions
deactivate
chown -R pihole-monitor:pihole-monitor /opt/pihole-monitor
chmod 755 /opt/pihole-monitor
chmod 600 /opt/pihole-monitor/.env

# Systemd service
cat > /etc/systemd/system/pihole-monitor.service << 'EOF'
[Unit]
Description=Pi-hole HA Monitor
After=network.target

[Service]
Type=simple
User=pihole-monitor
WorkingDirectory=/opt/pihole-monitor
ExecStart=/opt/pihole-monitor/venv/bin/python /opt/pihole-monitor/monitor.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start service
systemctl daemon-reload
systemctl enable pihole-monitor
systemctl start pihole-monitor
systemctl status pihole-monitor
```

**Test monitor:**
Open browser: `http://<monitor-ip>:8080`

### Step 5: Test Failover (5 min)

**Test 1: DNS via VIP**
```powershell
nslookup google.com <your-vip>
```

**Test 2: Failover**
```bash
# Stop primary Pi-hole
ssh root@<primary-ip> "systemctl stop pihole-FTL"

# Wait 15 seconds
Start-Sleep -Seconds 15

# Check monitor dashboard - secondary should be MASTER
# Check VIP moved to secondary
ssh root@<secondary-ip> "ip addr show | grep <your-vip>"

# Test DNS still works
nslookup google.com <your-vip>

# Start primary again
ssh root@<primary-ip> "systemctl start pihole-FTL"
```

## ⚙️ Integration with Nebula-sync

### What Nebula-sync Does (Keeps Working!)

Your current Nebula-sync configuration is perfect and continues to work:
```yaml
✅ SYNC_GRAVITY_GROUP=true          # Groups
✅ SYNC_GRAVITY_AD_LIST=true        # Adlists
✅ SYNC_GRAVITY_DOMAIN_LIST=true    # Black/whitelist/regex
✅ SYNC_GRAVITY_CLIENT=true         # Client assignments
✅ SYNC_GRAVITY_DHCP_LEASES=true    # DHCP reservations
✅ SYNC_CONFIG_DHCP=true            # DHCP config (without 'active')
✅ SYNC_CONFIG_DNS=true             # DNS hosts
```

### What Keepalived Does (New!)

```yaml
✅ Virtual IP (VIP) management       # Automatic move during failover
✅ Health monitoring                # Check if Pi-hole is healthy
✅ DHCP active/inactive toggle      # Switches DHCP on/off during failover
✅ Automatic failover               # Within 15 seconds
```

### Perfect Together

```
┌─────────────────────────────────────────────────────────┐
│                  Normal Operation                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Primary (10.10.100.10)         Secondary (10.10.100.20)│
│  ├── MASTER state               ├── BACKUP state        │
│  ├── Has VIP (10.10.100.1)      ├── No VIP             │
│  ├── DHCP active=true            ├── DHCP active=false  │
│  └── Serves DNS/DHCP             └── Standby           │
│                                                          │
│  ◄──────────── Nebula-sync every 12h ─────────────►    │
│  (Syncs: lists, groups, leases, settings)               │
│                                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              Failover Scenario                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Primary (10.10.100.10)         Secondary (10.10.100.20)│
│  ├── FAULT state                ├── MASTER state        │
│  ├── No VIP                      ├── Has VIP (10.10.100.1)│
│  ├── DHCP active=false           ├── DHCP active=true   │
│  └── Offline/Failed              └── Now serves DNS/DHCP│
│                                                          │
│  Keepalived detects failure → moves VIP → toggles DHCP  │
│  Nebula-sync ensures both have same data                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 📊 Monitor Dashboard

Open: `http://<monitor-ip>:8080`

You see:
- ✅ Status of both Pi-holes (online/offline)
- ✅ Which server is MASTER
- ✅ VIP status
- ✅ Query statistics
- ✅ Failover event history
- ✅ DHCP leases

## 🔧 Keepalived Scripts Explained

### check_pihole_service.sh
Checks if Pi-hole is healthy:
1. ✅ pihole-FTL service active
2. ✅ DNS responds locally
3. ✅ DHCP port open (if DHCP active=true)

**Important:** Only checks DHCP if `active=true` in pihole.toml!

### dhcp_control.sh
Toggle DHCP on/off:
```bash
# Enable: sets active=true in [dhcp] section
# Disable: sets active=false in [dhcp] section
# Restart pihole-FTL
```

**Perfect with Nebula-sync:** 
- Nebula-sync syncs DHCP settings BUT excludes 'active'
- Keepalived only manages 'active' flag
- No conflicts!

### keepalived_notify.sh
Triggered on state changes:
```bash
MASTER:  Enable DHCP + send ARP update
BACKUP:  Disable DHCP
FAULT:   Disable DHCP
```

## ⚠️ Important Notes

### DHCP 'active' Flag

**Nebula-sync configuration:**
```yaml
SYNC_CONFIG_DHCP=true
SYNC_CONFIG_DHCP_EXCLUDE=active  ← Crucial!
```

This ensures that:
- ✅ Nebula-sync: Syncs DHCP settings (range, router, etc.)
- ✅ Keepalived: Only manages 'active' flag
- ✅ No conflicts between sync and keepalived

### DHCP Leases

**Your Nebula-sync:**
```yaml
SYNC_GRAVITY_DHCP_LEASES=true  ← Perfect!
```

This syncs:
- ✅ Static DHCP reservations
- ✅ Client MAC/IP mappings
- ✅ Hostnames

**Keepalived has NO influence here** - continues via Nebula-sync!

### Sync Timing

```
Nebula-sync:  Every 12 hours (CRON=0 */12 * * *)
Keepalived:   Real-time health checks (every 5 sec)
```

Perfect combination:
- Nebula-sync: Configuration consistency
- Keepalived: Instant failover

## 🎯 Your Workflow

### Making Changes

**On Primary:**
1. Login: `http://<primary-ip>/admin`
2. Make changes (add blocklist, etc.)
3. Wait for Nebula-sync (max 12 hours) OR force sync:
   ```bash
   # If you run Nebula-sync container
   docker exec nebula-sync /app/sync.sh
   ```

### Failover Test

```bash
# Stop primary
ssh root@<primary-ip> "systemctl stop pihole-FTL"

# Check monitor dashboard
# Secondary takes over within 15 sec

# Check VIP
ssh root@<secondary-ip> "ip addr show"

# Start primary again
ssh root@<primary-ip> "systemctl start pihole-FTL"
```

### Status Check

```bash
# Keepalived status
ssh root@<primary-ip> "systemctl status keepalived"
ssh root@<secondary-ip> "systemctl status keepalived"

# Who has VIP?
ssh root@<primary-ip> "ip addr show | grep <your-vip>"
ssh root@<secondary-ip> "ip addr show | grep <your-vip>"

# DHCP status (in pihole.toml)
ssh root@<primary-ip> "grep -A5 '\[dhcp\]' /etc/pihole/pihole.toml | grep active"
ssh root@<secondary-ip> "grep -A5 '\[dhcp\]' /etc/pihole/pihole.toml | grep active"
```

## 🔍 Troubleshooting

### Keepalived Logs
```bash
ssh root@<primary-ip> "journalctl -u keepalived -n 50"
ssh root@<primary-ip> "tail -f /var/log/keepalived-notify.log"
```

### Pi-hole Status
```bash
ssh root@<primary-ip> "pihole status"
ssh root@<secondary-ip> "pihole status"
```

### VIP Issues
```bash
# Check VRRP traffic
ssh root@<primary-ip> "tcpdump -i eth0 vrrp"

# Check authentication password matches
ssh root@<primary-ip> "grep auth_pass /etc/keepalived/keepalived.conf"
ssh root@<secondary-ip> "grep auth_pass /etc/keepalived/keepalived.conf"
```

### Monitor Dashboard Offline
```bash
ssh root@<monitor-ip> "systemctl status pihole-monitor"
ssh root@<monitor-ip> "journalctl -u pihole-monitor -n 50"
```

## 📝 Configure Router/Clients

### Router DNS Settings
```
Primary DNS:   <your-vip>    ← VIP
Secondary DNS: 1.1.1.1       ← Backup (if both Pi-holes down)
```

### Client Static DNS
```
DNS Server 1: <your-vip>     ← VIP
DNS Server 2: <primary-ip>   ← Primary direct (backup)
```

## ✅ Checklist

- [ ] Keepalived installed on both Pi-holes
- [ ] Scripts copied to both servers
- [ ] Primary keepalived running & has VIP
- [ ] Secondary keepalived running & no VIP
- [ ] Monitor dashboard accessible
- [ ] Monitor shows both Pi-holes online
- [ ] DNS query via VIP works
- [ ] Failover test successful
- [ ] Nebula-sync continues working
- [ ] DHCP active flag toggled correctly
- [ ] Router/clients use VIP as DNS

## 🎉 Done!

You now have:
- ✅ Existing Pi-holes with Nebula-sync (keeps working)
- ✅ Keepalived for automatic failover (new!)
- ✅ Monitor dashboard for real-time status (new!)
- ✅ Virtual IP for transparent failover (new!)
- ✅ DHCP automatic toggle on failover (new!)

**Total added value:**
- Automatic failover within 15 seconds
- No manual intervention needed during issues
- Real-time monitoring and alerting
- Transparent for clients (always use VIP)

**Estimated setup time: 30-40 minutes**

Success! 🚀
