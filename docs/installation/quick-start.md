# Pi-hole Sentinel - Quick Start Guide (Fresh Install)

Deze guide is voor een **nieuwe installatie** vanaf scratch met alle security en performance fixes.

## 📋 Vereisten

Voordat je begint, zorg dat je hebt:

- ✅ 2 werkende Pi-holes (met DNS, Pi-hole v6.0+)
- ✅ SSH root access naar alle servers
- ✅ Pi-hole web interface wachtwoorden
- ✅ Vrije IP voor VIP (Virtual IP)
- ✅ (Optioneel) Aparte monitor server

---

## 🚀 Installatie in 5 Stappen

### Stap 1: Clone Repository

Op je **lokale machine** of **monitor server**:

```bash
git clone https://github.com/JBakers/pihole-sentinel.git
cd pihole-sentinel

# Checkout the testing branch (latest features)
git checkout testing
```

### Stap 2: Run Setup Script

```bash
sudo python3 setup.py
```

Het script vraagt om:

#### Network Configuratie
```
Network interface name [eth0]: eth0
Primary Pi-hole IP: 10.10.100.10
Secondary Pi-hole IP: 10.10.100.20
Virtual IP (VIP): 10.10.100.2
Network gateway IP: 10.10.100.1
```

#### DHCP Configuratie
```
Do you use DHCP on Pi-holes? [y/N]: y  # of n als je geen DHCP gebruikt
```

#### Monitor Server
```
Run monitor on separate server? [y/N]: y  # Aanbevolen
Monitor server IP: 10.10.100.30
SSH user [root]: root
SSH port [22]: 22
```

#### SSH Configuratie
```
SSH user [root]: root
SSH port [22]: 22
```

#### Wachtwoorden (1x nodig)
```
SSH password for root@10.10.100.10: ********
SSH password for root@10.10.100.20: ********
SSH password for root@10.10.100.30: ******** (monitor)
Primary Pi-hole web password: ********
Secondary Pi-hole web password: ********
```

### Stap 3: Deploy Automatisch

Kies deployment optie:

```
Select deployment option:
1) Generate configs only
2) Generate and deploy to all servers via SSH [RECOMMENDED]
3) Deploy to monitor server only
4) Deploy to primary Pi-hole only
5) Deploy to secondary Pi-hole only

Choice [2]: 2
```

Setup script zal nu **automatisch**:
- ✅ SSH keys genereren en distribueren
- ✅ Dependencies installeren op alle servers
- ✅ Keepalived configureren op beide Pi-holes
- ✅ Monitor service deployen
- ✅ Services starten
- ✅ Timezone configureren
- ✅ Sensitive files cleanup

**Wacht tot je ziet:**
```
┌─────────────────────────────────────────────────────┐
│         DEPLOYMENT COMPLETED SUCCESSFULLY!           │
└─────────────────────────────────────────────────────┘

All services deployed and started successfully!
You can now access the dashboard at: http://10.10.100.30:8080
```

### Stap 4: Genereer en Configureer API Key

**BELANGRIJK:** Na deployment moet je een API key toevoegen.

```bash
# Genereer een secure API key
python3 -c "import secrets; print('API_KEY=' + secrets.token_urlsafe(32))"
```

Output (voorbeeld):
```
API_KEY=XrZ9k2L4mN8pQ6vW1yT3hJ7bC5dF0gK9sA2eR4uI6oP8
```

**Voeg toe aan .env file:**

```bash
# Op monitor server
ssh root@10.10.100.30

# Voeg API key toe
echo "API_KEY=XrZ9k2L4mN8pQ6vW1yT3hJ7bC5dF0gK9sA2eR4uI6oP8" >> /opt/pihole-monitor/.env

# Restart monitor
systemctl restart pihole-monitor
```

**Bewaar deze key veilig!** Je hebt hem nodig voor alle API calls.

### Stap 5: Verificatie

**Check services draaien:**

```bash
# Op monitor server
ssh root@10.10.100.30 systemctl status pihole-monitor

# Op beide Pi-holes
ssh root@10.10.100.10 systemctl status keepalived
ssh root@10.10.100.20 systemctl status keepalived
```

Alles moet **active (running)** zijn.

**Test dashboard:**

Open in browser: `http://10.10.100.30:8080`

Je ziet de dashboard, maar API calls falen (403) - dit is normaal omdat de frontend nog geen API key heeft.

**Test API met curl:**

```bash
# Test zonder API key (moet 403 geven)
curl http://10.10.100.30:8080/api/status

# Test met API key (moet 200 + JSON geven)
curl -H "X-API-Key: XrZ9k2L4mN8pQ6vW1yT3hJ7bC5dF0gK9sA2eR4uI6oP8" \
     http://10.10.100.30:8080/api/status | jq .
```

**Verwachte output:**
```json
{
  "timestamp": "2024-...",
  "primary": {
    "ip": "10.10.100.10",
    "name": "Primary Pi-hole",
    "state": "MASTER",
    "has_vip": true,
    "online": true,
    "pihole": true,
    "dns": true,
    "dhcp": true
  },
  "secondary": {
    "ip": "10.10.100.20",
    "name": "Secondary Pi-hole",
    "state": "BACKUP",
    "has_vip": false,
    ...
  }
}
```

---

## ✅ Snelle Test Checklist

Voer deze tests uit om te verifiëren dat alles werkt:

### 1. API Security Test

```bash
API_KEY="jouw-api-key-hier"
MONITOR="10.10.100.30:8080"

# Moet 403 geven
curl http://$MONITOR/api/status
echo "Expected: 403 Forbidden ✓"

# Moet 200 geven
curl -H "X-API-Key: $API_KEY" http://$MONITOR/api/status
echo "Expected: 200 OK with JSON ✓"
```

### 2. VIP Check

```bash
# Check welke Pi-hole de VIP heeft
ssh root@10.10.100.10 "ip addr show | grep 10.10.100.2"
ssh root@10.10.100.20 "ip addr show | grep 10.10.100.2"
```

**Verwacht:** VIP zichtbaar op 1 van de 2 Pi-holes (de MASTER)

### 3. Monitoring Check

```bash
# Check dat monitoring elke 10s update
ssh root@10.10.100.30 "tail -f /var/log/pihole-monitor.log"
```

Je moet elke 10 seconden status updates zien.

### 4. Failover Test

**Trigger failover:**

```bash
# Identificeer MASTER (die met VIP)
# Stop Pi-hole op MASTER
ssh root@10.10.100.10 systemctl stop pihole-FTL

# Monitor logs voor failover
ssh root@10.10.100.30 journalctl -u pihole-monitor -f
```

**Verwacht binnen 30 seconden:**
```
FAILOVER: Secondary is now MASTER
```

**Restore:**
```bash
ssh root@10.10.100.10 systemctl start pihole-FTL
```

✅ **PASS** als failover en failback beide werken

---

## 🔧 Dashboard Frontend Update (Optioneel)

Om de dashboard volledig werkend te krijgen (zodat je niet elke keer curl hoeft te gebruiken), moet de frontend de API key meesturen.

**Optie 1: Environment Variable (Veiligst)**

De frontend kan de API key ophalen uit een configuratie endpoint. Dit vergt aanpassingen aan `index.html` en `settings.html`.

**Optie 2: Hardcode (Alleen voor testing!)**

Voor snelle test kun je de key hardcoden in de HTML files:

```bash
# Op monitor server
cd /opt/pihole-monitor

# Backup
cp index.html index.html.backup
cp settings.html settings.html.backup

# Voeg API key toe aan fetch calls
# In index.html, zoek naar alle fetch() calls en voeg toe:
headers: {
    'X-API-Key': 'jouw-api-key-hier'
}
```

**Voorbeeld:**
```javascript
// Voor:
fetch('/api/status')

// Na:
fetch('/api/status', {
    headers: {
        'X-API-Key': 'XrZ9k2L4mN8pQ6vW1yT3hJ7bC5dF0gK9sA2eR4uI6oP8'
    }
})
```

⚠️ **Waarschuwing:** Hardcoded keys zijn zichtbaar in browser source. Alleen voor private netwerken!

---

## 📊 Wat Heb Je Nu?

Na deze setup heb je:

### ✅ Security Features
- 🔐 API key authenticatie op alle endpoints
- 🛡️ CORS restricted tot localhost
- 🚫 Geen credential leakage endpoints
- 🔒 Passwords veilig via environment variables (niet in process list)
- ✅ Input validatie op alle user inputs
- 🔄 Up-to-date dependencies met security patches

### ✅ Performance Features
- ⚡ Rate limiting (3 req/60s per IP)
- 🔄 Connection pooling (hergebruik HTTP sessies)
- 🚀 Async subprocess calls (geen blocking)
- 📊 Database indexes (snelle queries)
- 📝 Log rotation (10MB max, 5 backups)

### ✅ Monitoring Features
- 👁️ Real-time status elke 10 seconden
- 🔄 Automatische VIP detectie
- 📈 Historical data & graphs
- 🔔 Notification support (Telegram, Discord, etc)
- 📋 Event logging

### ✅ HA Features
- 🔄 Automatische failover (<30s)
- 💾 DHCP failover (indien ingeschakeld)
- 🔁 Automatische failback
- 🎯 VIP management via Keepalived

---

## 🎯 Je Bent Production Ready Als:

- ✅ Alle services running (check via `systemctl status`)
- ✅ API key geconfigureerd (niet de temporary key!)
- ✅ Beide Pi-holes bereikbaar via SSH
- ✅ VIP actief op 1 Pi-hole
- ✅ Dashboard bereikbaar via browser
- ✅ API tests PASS (403 zonder key, 200 met key)
- ✅ Failover test geslaagd (< 30 seconden)
- ✅ Logs zonder errors na 1 uur draaien

---

## 📝 Belangrijke Endpoints

### Dashboard
- **Main Dashboard:** http://10.10.100.30:8080
- **Settings:** http://10.10.100.30:8080/settings.html

### API (met X-API-Key header)
- **Status:** GET /api/status
- **History:** GET /api/history?hours=24
- **Events:** GET /api/events?limit=50
- **Notifications:** GET/POST /api/notifications/settings

---

## 🐛 Veel Voorkomende Problemen

### "Connection refused" naar monitor

**Check:**
```bash
ssh root@10.10.100.30 systemctl status pihole-monitor
ssh root@10.10.100.30 journalctl -u pihole-monitor -n 50
```

**Fix:**
```bash
ssh root@10.10.100.30 systemctl restart pihole-monitor
```

### "403 Forbidden" bij alle API calls (zelfs met key)

**Check of API key correct is:**
```bash
ssh root@10.10.100.30 cat /opt/pihole-monitor/.env | grep API_KEY
```

**Restart na wijziging:**
```bash
ssh root@10.10.100.30 systemctl restart pihole-monitor
```

### Failover werkt niet

**Check keepalived op beide nodes:**
```bash
ssh root@10.10.100.10 systemctl status keepalived
ssh root@10.10.100.20 systemctl status keepalived

# Check VRRP traffic
ssh root@10.10.100.10 'tcpdump -n -i any vrrp | head -20'
```

**Check VIP configuratie:**
```bash
ssh root@10.10.100.10 cat /etc/keepalived/keepalived.conf | grep virtual_router_id
ssh root@10.10.100.20 cat /etc/keepalived/keepalived.conf | grep virtual_router_id
```

Beide moeten **hetzelfde** virtual_router_id hebben!

---

## 📚 Meer Informatie

Voor uitgebreide tests en troubleshooting, zie:
- **[Testing Guide](../development/testing.md)** - Volledige test suite met 20+ tests
- **[README.md](../../README.md)** - Algemene documentatie
- **[Configuration Sync](../maintenance/sync.md)** - Configuratie synchronisatie

---

## 🎉 Klaar!

Je Pi-hole Sentinel HA setup is nu operationeel met:
- ✅ Alle security fixes
- ✅ Performance optimalisaties
- ✅ Production-ready configuratie

**Geniet van je High Availability Pi-hole setup! 🚀**

Voor vragen of problemen: https://github.com/JBakers/pihole-sentinel/issues
