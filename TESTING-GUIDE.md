# Pi-hole Sentinel - Testing Guide

Dit document helpt je om alle security en performance fixes te testen na deployment.

## 📋 Pre-Test Checklist

Voordat je begint met testen:

- [ ] Backup gemaakt van bestaande configuratie
- [ ] Nieuwe versie files beschikbaar (via setup.py of handmatige copy)
- [ ] Dependencies geüpdatet (`pip install --upgrade -r requirements.txt`)
- [ ] `.env` file geconfigureerd met API_KEY
- [ ] Services herstart

**⚠️ BELANGRIJK:** Gebruik NOOIT `git pull` op productie servers! Deploy altijd via `setup.py` of kopieer de specifieke bestanden handmatig.

## 🔧 Deployment Stappen

### 1. Update Dependencies

```bash
# Op monitor server
cd /opt/pihole-monitor
source venv/bin/activate
pip install --upgrade -r /path/to/pihole-sentinel/requirements.txt
```

Verwachte output:
```
Successfully installed fastapi-0.115.0 uvicorn-0.30.0 aiohttp-3.10.0 ...
```

### 2. Update Code

```bash
# Backup oude versie
sudo cp /opt/pihole-monitor/monitor.py /opt/pihole-monitor/monitor.py.backup

# Copy nieuwe versie
sudo cp /path/to/pihole-sentinel/dashboard/monitor.py /opt/pihole-monitor/monitor.py
sudo chown pihole-monitor:pihole-monitor /opt/pihole-monitor/monitor.py
```

### 3. Configureer API Key

Genereer een secure API key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Voeg toe aan `/opt/pihole-monitor/.env`:
```bash
API_KEY=<jouw-gegenereerde-key-hier>
```

### 4. Restart Service

```bash
sudo systemctl restart pihole-monitor
sudo systemctl status pihole-monitor
```

Verwacht: `active (running)`

---

## ✅ Test 1: Critical Security Fixes

### Test 1.1: API Authentication

**Test zonder API key:**
```bash
curl -X GET http://localhost:8080/api/status
```

**Verwacht:**
```json
{"detail":"Not authenticated"}
```
Status code: **403**

**Test met correcte API key:**
```bash
curl -X GET http://localhost:8080/api/status \
  -H "X-API-Key: <jouw-api-key>"
```

**Verwacht:**
```json
{
  "timestamp": "2024-...",
  "primary": {...},
  "secondary": {...}
}
```
Status code: **200**

✅ **PASS** als zonder key 403 geeft en met key 200

### Test 1.2: CORS Policy

**Test met ongeldige origin:**
```bash
curl -X GET http://localhost:8080/api/status \
  -H "X-API-Key: <jouw-api-key>" \
  -H "Origin: http://evil.com" \
  -v
```

**Verwacht:**
Geen `Access-Control-Allow-Origin: http://evil.com` in response headers

✅ **PASS** als evil.com niet in CORS headers staat

### Test 1.3: Removed Insecure Endpoint

**Test verwijderd endpoint:**
```bash
curl -X GET http://localhost:8080/api/notifications/test-settings \
  -H "X-API-Key: <jouw-api-key>"
```

**Verwacht:**
```json
{"detail":"Not Found"}
```
Status code: **404**

✅ **PASS** als endpoint niet meer bestaat

### Test 1.4: Password Security

**Test sshpass niet in process list:**
```bash
# Tijdens setup.py run (op aparte machine):
ps aux | grep sshpass
```

**Verwacht:**
Geen `-p password` zichtbaar, alleen `-e` flag

✅ **PASS** als passwords niet in process list staan

---

## ⚡ Test 2: Performance Improvements

### Test 2.1: Rate Limiting

**Test rate limit:**
```bash
# Verstuur 4 requests snel achter elkaar
for i in {1..4}; do
  curl -X POST http://localhost:8080/api/notifications/test \
    -H "X-API-Key: <jouw-api-key>" \
    -H "Content-Type: application/json" \
    -d '{"service":"telegram","settings":{"bot_token":"test","chat_id":"test"}}'
  echo "Request $i"
done
```

**Verwacht:**
- Eerste 3 requests: 400 (ongeldige credentials) of 500
- 4e request: **429** "Rate limit exceeded"

✅ **PASS** als 4e request 429 geeft

### Test 2.2: Connection Pooling

**Check logs voor session creation:**
```bash
sudo journalctl -u pihole-monitor -f
```

**Verwacht in logs:**
Geen herhaalde "Creating new session" berichten elke 10 seconden

✅ **PASS** als session maar 1x wordt aangemaakt

### Test 2.3: Async Performance

**Check blocking operations:**
```bash
# Monitor should respond fast even during checks
time curl -X GET http://localhost:8080/api/status \
  -H "X-API-Key: <jouw-api-key>"
```

**Verwacht:**
Response tijd < 500ms (was 2-3s met blocking calls)

✅ **PASS** als response snel is

### Test 2.4: Database Indexes

**Check indexes aanwezig:**
```bash
sqlite3 /opt/pihole-monitor/monitor.db ".indexes"
```

**Verwacht:**
```
idx_events_timestamp
idx_events_type
idx_status_timestamp
```

✅ **PASS** als alle 3 indexes bestaan

### Test 2.5: Log Rotation

**Check log configuratie:**
```bash
ls -lh /var/log/pihole-monitor.log*
```

**Verwacht:**
Bij logs > 10MB zie je `.1`, `.2` etc backup files

```bash
# Force log rotation test (optioneel)
python3 << 'EOF'
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    '/tmp/test.log',
    maxBytes=100,  # 100 bytes voor test
    backupCount=3
)
logger = logging.getLogger('test')
logger.addHandler(handler)
logger.setLevel(logging.INFO)

for i in range(100):
    logger.info(f"Test message {i}" * 10)
EOF

ls -lh /tmp/test.log*
```

**Verwacht:**
Meerdere `.log.1`, `.log.2` files

✅ **PASS** als rotation werkt

---

## 🔍 Test 3: Functionality Tests

### Test 3.1: Dashboard Toegankelijk

**Open in browser:**
```
http://<monitor-ip>:8080
```

**Verwacht:**
Dashboard laadt, maar API calls falen zonder API key in JS

### Test 3.2: API Endpoints

**Test alle endpoints:**

```bash
API_KEY="<jouw-api-key>"
HOST="http://localhost:8080"

# Status
curl -s "$HOST/api/status" -H "X-API-Key: $API_KEY" | jq .

# History
curl -s "$HOST/api/history?hours=1" -H "X-API-Key: $API_KEY" | jq .

# Events
curl -s "$HOST/api/events?limit=10" -H "X-API-Key: $API_KEY" | jq .

# Notification settings (read)
curl -s "$HOST/api/notifications/settings" -H "X-API-Key: $API_KEY" | jq .
```

**Verwacht:**
Alle endpoints geven 200 + JSON data

✅ **PASS** als alle endpoints werken

### Test 3.3: Monitoring Loop

**Check status updates:**
```bash
# Watch database updates
watch -n 2 'sqlite3 /opt/pihole-monitor/monitor.db "SELECT timestamp FROM status_history ORDER BY timestamp DESC LIMIT 1"'
```

**Verwacht:**
Timestamp update elke 10 seconden

✅ **PASS** als updates regelmatig komen

### Test 3.4: VIP Detection

**Check VIP status:**
```bash
curl -s http://localhost:8080/api/status \
  -H "X-API-Key: <jouw-api-key>" | \
  jq '.primary.has_vip, .secondary.has_vip'
```

**Verwacht:**
```
true
false
```
(of omgekeerd, maar 1 moet true zijn)

✅ **PASS** als precies 1 node VIP heeft

---

## 🔄 Test 4: Failover Test

### Setup

**Op MASTER Pi-hole:**
```bash
# Check welke node MASTER is
curl -s http://<monitor-ip>:8080/api/status \
  -H "X-API-Key: <jouw-api-key>" | jq '.primary.state, .secondary.state'
```

### Failover Trigger

**Stop Pi-hole op MASTER:**
```bash
# Op MASTER node
sudo systemctl stop pihole-FTL
```

### Verificatie

**Monitor logs:**
```bash
# Op monitor server
sudo journalctl -u pihole-monitor -f
```

**Verwacht binnen 30 seconden:**
```
FAILOVER: Secondary is now MASTER
```

**Check nieuwe status:**
```bash
curl -s http://<monitor-ip>:8080/api/status \
  -H "X-API-Key: <jouw-api-key>" | \
  jq '.primary.state, .secondary.state'
```

**Verwacht:**
States zijn omgedraaid

**Check VIP:**
```bash
# Op beide Pi-holes
ip addr show | grep <vip-address>
```

VIP nu op secondary node

### Restore

```bash
# Start Pi-hole weer
sudo systemctl start pihole-FTL

# Monitor failback
sudo journalctl -u pihole-monitor -f
```

✅ **PASS** als failover binnen 30s werkt en failback ook

---

## 📊 Test Results Template

Vul dit in tijdens testen:

```
=== Pi-hole Sentinel Test Results ===
Datum: __________
Versie: 0.9.0-beta.1

CRITICAL SECURITY:
[ ] Test 1.1: API Authentication          ✅ / ❌
[ ] Test 1.2: CORS Policy                 ✅ / ❌
[ ] Test 1.3: Removed Endpoint            ✅ / ❌
[ ] Test 1.4: Password Security           ✅ / ❌

PERFORMANCE:
[ ] Test 2.1: Rate Limiting               ✅ / ❌
[ ] Test 2.2: Connection Pooling          ✅ / ❌
[ ] Test 2.3: Async Performance           ✅ / ❌
[ ] Test 2.4: Database Indexes            ✅ / ❌
[ ] Test 2.5: Log Rotation                ✅ / ❌

FUNCTIONALITY:
[ ] Test 3.1: Dashboard Access            ✅ / ❌
[ ] Test 3.2: API Endpoints               ✅ / ❌
[ ] Test 3.3: Monitoring Loop             ✅ / ❌
[ ] Test 3.4: VIP Detection               ✅ / ❌

FAILOVER:
[ ] Test 4: Failover & Failback           ✅ / ❌

Opmerkingen:
___________________________________________
___________________________________________
```

---

## 🐛 Troubleshooting

### API Authentication Werkt Niet

**Probleem:** 403 met correcte key

**Check:**
```bash
# Verify API key in .env
sudo cat /opt/pihole-monitor/.env | grep API_KEY

# Check service laadde .env
sudo systemctl restart pihole-monitor
sudo journalctl -u pihole-monitor | grep "API Key"
```

**Fix:**
Zie warning in logs voor gegenereerde temporary key, of configureer permanent key.

### Rate Limiting Te Streng

**Probleem:** Legitieme requests geblokkeerd

**Fix:**
Verhoog limiet in `monitor.py`:
```python
RATE_LIMIT_REQUESTS = 10  # Was 3
RATE_LIMIT_WINDOW = 60
```

### Dashboard Laadt Niet

**Probleem:** Witte pagina, geen data

**Check browser console:**
```
Failed to fetch: 403 Forbidden
```

**Fix:**
Dashboard moet API key meesturen. Update `index.html` en `settings.html` met:
```javascript
headers: {
    'X-API-Key': 'your-key-here'  // Voeg toe
}
```

### Connection Pooling Issues

**Probleem:** "Session closed" errors

**Check:**
```bash
sudo journalctl -u pihole-monitor | grep "session"
```

**Fix:**
Service herstart lost dit op. Session wordt opnieuw aangemaakt.

---

## 📝 Post-Test Actions

Na succesvolle tests:

1. **Documenteer resultaten** - Vul test template in
2. **Configureer monitoring** - Setup externe monitoring (Uptime Kuma, etc)
3. **Backup configuratie** - Maak backup van werkende setup
4. **Update documentatie** - Voeg API key instructies toe aan README
5. **Plan maintenance** - Schema voor dependency updates

---

## 🎯 Success Criteria

Project is **production ready** als:

- ✅ Alle Critical Security tests PASS
- ✅ Minimaal 4/5 Performance tests PASS
- ✅ Alle Functionality tests PASS
- ✅ Failover test PASS (< 30s)
- ✅ Geen errors in logs na 1 uur draaien
- ✅ API key geconfigureerd (niet temporary key)
- ✅ CORS policy aangepast voor jouw IPs

---

## 📞 Support

Bij problemen:

1. Check logs: `sudo journalctl -u pihole-monitor -n 100`
2. Check GitHub issues: https://github.com/JBakers/pihole-sentinel/issues
3. Review audit report voor extra context

---

**Good luck met testen! 🚀**
