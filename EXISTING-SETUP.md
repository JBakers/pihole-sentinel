# Pi-hole HA - Voor Bestaande Pi-holes

## 🎯 Voor Gebruikers Met Werkende Pi-holes

Je hebt al werkende Pi-holes en wilt:
- ⚙️ Keepalived toevoegen voor automatische failover (Virtual IP)
- 📊 Monitor dashboard voor real-time status
- 🔄 Optioneel: Verbeterde sync die ook DHCP leases synct

**Deze guide is voor jou als:**
- ✅ Je hebt 2 werkende Pi-holes
- ✅ Je hebt optioneel al sync (Nebula-sync, Gravity-sync, etc.)
- ✅ Je wilt HA toevoegen zonder je bestaande setup te verstoren

## 🚀 Quick Setup (30 minuten)

### Stap 1: Genereer Configuraties (5 min)

**Op je Windows machine (of Linux werkstation):**

```powershell
# Navigeer naar de monitoring folder
cd c:\Users\jbake\.vscode\Workspace\monitoring\pihole-ha

# Of op Linux:
# cd /path/to/monitoring/pihole-ha

# Run setup script
python3 setup.py
```

**Het script vraagt om:**
```
Network interface (bijv: eth0, ens18)
Primary Pi-hole IP
Secondary Pi-hole IP
Virtual IP (VIP) - Kies een VRIJ IP in je netwerk
Gateway IP (je router)
Pi-hole wachtwoorden (voor API toegang)
```

**💡 Tips:**
- VIP moet een ongebruikt IP zijn in hetzelfde subnet
- Gebruik het web interface wachtwoord van je Pi-holes
- Netmask is meestal 24 voor /24 netwerken

**Resultaat:** Alle configuratie bestanden in `generated_configs/`

### Stap 2: Deploy Keepalived op Primary (10 min)

```powershell
# Kopieer bestanden
scp generated_configs/primary_keepalived.conf root@10.10.100.10:/tmp/
scp generated_configs/primary.env root@10.10.100.10:/tmp/
scp keepalived/scripts/*.sh root@10.10.100.10:/tmp/
```

**SSH naar primary:**
```bash
ssh root@10.10.100.10

# Installeer keepalived (als nog niet geïnstalleerd)
apt update && apt install -y keepalived arping

# Deploy configuratie
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

# Verify VIP is toegewezen
ip addr show | grep 10.10.100.1  # (of jouw gekozen VIP)
```

### Stap 3: Deploy Keepalived op Secondary (10 min)

```powershell
# Kopieer bestanden
scp generated_configs/secondary_keepalived.conf root@10.10.100.20:/tmp/
scp generated_configs/secondary.env root@10.10.100.20:/tmp/
scp keepalived/scripts/*.sh root@10.10.100.20:/tmp/
```

**SSH naar secondary:**
```bash
ssh root@10.10.100.20

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

# VIP zou NIET zichtbaar moeten zijn (backup node)
ip addr show | grep 10.10.100.1
```

### Stap 4: Deploy Monitor Dashboard (10 min)

```powershell
# Kopieer bestanden naar monitor
scp dashboard/monitor.py root@10.10.100.99:/tmp/
scp dashboard/index.html root@10.10.100.99:/tmp/
scp generated_configs/monitor.env root@10.10.100.99:/tmp/
```

**SSH naar monitor:**
```bash
ssh root@10.10.100.99

# Installeer dependencies (als nog niet gedaan)
apt update
apt install -y python3 python3-pip python3-venv

# Setup applicatie
mkdir -p /opt/pihole-monitor
cd /opt/pihole-monitor

# Kopieer bestanden
cp /tmp/monitor.py .
cp /tmp/index.html .
cp /tmp/monitor.env .env

# Python environment
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn aiohttp aiosqlite python-dotenv

# Maak service user
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
Open browser: `http://10.10.100.99:8080`

### Stap 5: Test Failover (5 min)

**Test 1: DNS via VIP**
```powershell
nslookup google.com 10.10.100.1
```

**Test 2: Failover**
```bash
# Stop primary Pi-hole
ssh root@10.10.100.10 "systemctl stop pihole-FTL"

# Wacht 15 seconden
Start-Sleep -Seconds 15

# Check monitor dashboard - secondary zou MASTER moeten zijn
# Check VIP is verplaatst naar secondary
ssh root@10.10.100.20 "ip addr show | grep 10.10.100.1"

# Test DNS nog werkt
nslookup google.com 10.10.100.1

# Start primary weer
ssh root@10.10.100.10 "systemctl start pihole-FTL"
```

## ⚙️ Integratie met Nebula-sync

### Wat Nebula-sync Doet (Blijft Werken!)

Je huidige Nebula-sync configuratie is perfect en blijft gewoon werken:
```yaml
✅ SYNC_GRAVITY_GROUP=true          # Groups
✅ SYNC_GRAVITY_AD_LIST=true        # Adlists
✅ SYNC_GRAVITY_DOMAIN_LIST=true    # Black/whitelist/regex
✅ SYNC_GRAVITY_CLIENT=true         # Client assignments
✅ SYNC_GRAVITY_DHCP_LEASES=true    # DHCP reserveringen
✅ SYNC_CONFIG_DHCP=true            # DHCP config (zonder 'active')
✅ SYNC_CONFIG_DNS=true             # DNS hosts
```

### Wat Keepalived Doet (Nieuw!)

```yaml
✅ Virtual IP (VIP) management       # Automatisch verplaatsen bij failover
✅ Health monitoring                # Check of Pi-hole gezond is
✅ DHCP active/inactive toggle      # Schakelt DHCP aan/uit bij failover
✅ Automatic failover               # Binnen 15 seconden
```

### Perfect Samenspel

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

Open: `http://10.10.100.99:8080`

Je ziet:
- ✅ Status beide Pi-holes (online/offline)
- ✅ Welke server MASTER is
- ✅ VIP status
- ✅ Query statistics
- ✅ Failover event geschiedenis
- ✅ DHCP leases

## 🔧 Keepalived Scripts Uitleg

### check_pihole_service.sh
Controleert of Pi-hole gezond is:
1. ✅ pihole-FTL service actief
2. ✅ DNS reageert lokaal
3. ✅ DHCP port open (als DHCP active=true)

**Belangrijk:** Checkt DHCP alleen als `active=true` in pihole.toml!

### dhcp_control.sh
Toggle DHCP aan/uit:
```bash
# Enable: zet active=true in [dhcp] sectie
# Disable: zet active=false in [dhcp] sectie
# Restart pihole-FTL
```

**Perfect met Nebula-sync:** 
- Nebula-sync synct DHCP settings MAAR sluit 'active' uit
- Keepalived beheert alleen 'active' flag
- Geen conflicts!

### keepalived_notify.sh
Triggered bij state changes:
```bash
MASTER:  Enable DHCP + send ARP update
BACKUP:  Disable DHCP
FAULT:   Disable DHCP
```

## ⚠️ Belangrijke Notities

### DHCP 'active' Flag

**Nebula-sync configuratie:**
```yaml
SYNC_CONFIG_DHCP=true
SYNC_CONFIG_DHCP_EXCLUDE=active  ← Cruciaal!
```

Dit zorgt ervoor dat:
- ✅ Nebula-sync: Synct DHCP settings (range, router, etc.)
- ✅ Keepalived: Beheert alleen 'active' flag
- ✅ Geen conflicts tussen sync en keepalived

### DHCP Leases

**Jouw Nebula-sync:**
```yaml
SYNC_GRAVITY_DHCP_LEASES=true  ← Perfect!
```

Dit synct:
- ✅ Statische DHCP reserveringen
- ✅ Client MAC/IP mappings
- ✅ Hostnames

**Keepalived heeft hier GEEN invloed op** - blijft gewoon via Nebula-sync!

### Sync Timing

```
Nebula-sync:  Elke 12 uur (CRON=0 */12 * * *)
Keepalived:   Real-time health checks (elke 5 sec)
```

Perfect combinatie:
- Nebula-sync: Configuratie consistency
- Keepalived: Instant failover

## 🎯 Jouw Workflow

### Wijzigingen Maken

**Op Primary (10.10.100.10):**
1. Login: `http://10.10.100.10/admin`
2. Maak wijzigingen (add blocklist, etc.)
3. Wacht op Nebula-sync (max 12 uur) OF force sync:
   ```bash
   # Als je Nebula-sync container draait
   docker exec nebula-sync /app/sync.sh
   ```

### Failover Test

```bash
# Stop primary
ssh root@10.10.100.10 "systemctl stop pihole-FTL"

# Check monitor dashboard
# Secondary neemt over binnen 15 sec

# Check VIP
ssh root@10.10.100.20 "ip addr show"

# Start primary weer
ssh root@10.10.100.10 "systemctl start pihole-FTL"
```

### Status Check

```bash
# Keepalived status
ssh root@10.10.100.10 "systemctl status keepalived"
ssh root@10.10.100.20 "systemctl status keepalived"

# Wie heeft VIP?
ssh root@10.10.100.10 "ip addr show | grep 10.10.100.1"
ssh root@10.10.100.20 "ip addr show | grep 10.10.100.1"

# DHCP status (in pihole.toml)
ssh root@10.10.100.10 "grep -A5 '\[dhcp\]' /etc/pihole/pihole.toml | grep active"
ssh root@10.10.100.20 "grep -A5 '\[dhcp\]' /etc/pihole/pihole.toml | grep active"
```

## 🔍 Troubleshooting

### Keepalived Logs
```bash
ssh root@10.10.100.10 "journalctl -u keepalived -n 50"
ssh root@10.10.100.10 "tail -f /var/log/keepalived-notify.log"
```

### Pi-hole Status
```bash
ssh root@10.10.100.10 "pihole status"
ssh root@10.10.100.20 "pihole status"
```

### VIP Problemen
```bash
# Check VRRP traffic
ssh root@10.10.100.10 "tcpdump -i eth0 vrrp"

# Check authentication password matches
ssh root@10.10.100.10 "grep auth_pass /etc/keepalived/keepalived.conf"
ssh root@10.10.100.20 "grep auth_pass /etc/keepalived/keepalived.conf"
```

### Monitor Dashboard Offline
```bash
ssh root@10.10.100.99 "systemctl status pihole-monitor"
ssh root@10.10.100.99 "journalctl -u pihole-monitor -n 50"
```

## 📝 Router/Clients Configureren

### Router DNS Settings
```
Primary DNS:   10.10.100.1  ← VIP
Secondary DNS: 1.1.1.1       ← Backup (als beide Pi-holes down)
```

### Client Static DNS
```
DNS Server 1: 10.10.100.1    ← VIP
DNS Server 2: 10.10.100.10   ← Primary direct (backup)
```

## ✅ Checklist

- [ ] Keepalived geïnstalleerd op beide Pi-holes
- [ ] Scripts gekopieerd naar beide servers
- [ ] Primary keepalived running & heeft VIP
- [ ] Secondary keepalived running & geen VIP
- [ ] Monitor dashboard toegankelijk
- [ ] Monitor toont beide Pi-holes online
- [ ] DNS query via VIP werkt
- [ ] Failover test succesvol
- [ ] Nebula-sync blijft werken
- [ ] DHCP active flag wordt correct getoggled
- [ ] Router/clients gebruiken VIP als DNS

## 🎉 Klaar!

Je hebt nu:
- ✅ Bestaande Pi-holes met Nebula-sync (blijft werken)
- ✅ Keepalived voor automatische failover (nieuw!)
- ✅ Monitor dashboard voor real-time status (nieuw!)
- ✅ Virtual IP voor transparante failover (nieuw!)
- ✅ DHCP automatic toggle bij failover (nieuw!)

**Total added value:**
- Automatische failover binnen 15 seconden
- Geen handmatige interventie nodig bij problemen
- Real-time monitoring en alerting
- Transparant voor clients (gebruiken altijd VIP)

**Geschatte setup tijd: 30-40 minuten**

Succes! 🚀
