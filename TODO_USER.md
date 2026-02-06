# User TODO's

## Huidige Status
- **Branch:** develop
- **Versie:** 0.12.0-beta.7
- **Laatste audit:** 2026-02-06 (Docker test environment + full GUI audit)

---

## 🔴 BUGS — Hoge Prioriteit

### B1. index.html: System Commands JS niet in `<script>` tag
**Locatie:** `dashboard/index.html` regels ~1090-1210  
**Probleem:** Na de command-modal `</div>` staat ~120 regels JavaScript direct in de HTML body als raw tekst (zichtbaar voor gebruiker). Mist `<script>` en `</script>` tags.  
**Impact:** Commands sectie werkt niet, JS is zichtbaar als tekst in de footer.

### B2. index.html: System Commands card fout genest in footer div
**Locatie:** `dashboard/index.html` regel ~1030  
**Probleem:** De System Commands card + modal zitten **binnen** `<div class="footer">` in plaats van ervoor. Footer structuur is kapot.  
**Impact:** Footer layout is verkeerd, commands card styling valt in footer context.

### B3. monitor.py: `/api/commands/{name}` endpoint ONTBREEKT
**Locatie:** `dashboard/monitor.py`  
**Probleem:** De System Commands in index.html callen `POST /api/commands/monitor_status` etc. maar er bestaat GEEN `/api/commands` route in monitor.py.  
**Impact:** Alle 6 command buttons geven 404/405.

### B4. monitor.py: SnoozeResponse model mismatch → 500 error
**Locatie:** `dashboard/monitor.py` regels 182-186 vs 1996  
**Probleem:** Model verwacht `snoozed` (bool) + `remaining_seconds` (int), maar endpoint retourneert `enabled` + `active`.  
**Impact:** `GET /api/notifications/snooze` geeft altijd 500 Internal Server Error.

### B5. monitor.py: DHCP warning spam elke monitor cycle
**Locatie:** `dashboard/monitor.py` regels ~1349-1365  
**Probleem:** "DHCP misconfiguration" warning wordt elke 5s gelogd als event zonder debounce/dedup.  
**Impact:** Events tabel gevuld met 19x dezelfde warning binnen 2 minuten.

### B6. monitor.py: CONFIG key mismatch in failover notification
**Locatie:** `dashboard/monitor.py` regels ~1305-1310  
**Probleem:** Gebruikt `CONFIG.get('primary_name')` maar CONFIG gebruikt geneste dicts: `CONFIG["primary"]["name"]`. Retourneert `None`.  
**Impact:** Notification template variabelen `{primary}` en `{secondary}` zijn `None`.

---

## 🟡 BUGS — Medium Prioriteit

### B7. monitor.py: Duplicate "Monitor started" event
**Locatie:** `dashboard/monitor.py` regel 201 + 1206  
**Probleem:** "Monitor started" wordt 2x gelogd: in `lifespan` startup en in `monitor_loop` eerste iteratie.  
**Impact:** Twee "Monitor started" events bij elke herstart.

### B8. monitor.py: `dhcp_leases` altijd 0 als geen MASTER
**Locatie:** `dashboard/monitor.py` regels ~1266-1270  
**Probleem:** Leases worden alleen geteld van de MASTER node. Als geen node MASTER is (VIP down), is het altijd 0.  
**Impact:** Dashboard toont 0 leases terwijl Pi-holes wel leases serveren.

### B9. Dashboard API key hardcoded als `YOUR_API_KEY_HERE`
**Locatie:** `dashboard/index.html` regel 1226, `dashboard/settings.html` regel 1101  
**Probleem:** `setup.py` vervangt dit met `sed` bij deploy, maar in Docker test werkt niets. Geen runtime injection mechanisme.  
**Impact:** Dashboard doet 403 op elke API call in Docker test. Alleen bruikbaar na `setup.py` deploy.

### B10. LOCAL_SETUP.md compleet verouderd
**Locatie:** `LOCAL_SETUP.md`  
**Probleem:** Verwijst naar oude 172.20.0.x subnet, `docker-compose` v1, Redis container, `python:3.14-slim`. Matcht niet meer met de huidige `docker-compose.test.yml`.  
**Impact:** Misleidende documentatie voor contributors.

---

## 🟢 Verbeteringen — Functionaliteit

### F1. API key runtime injection voor Docker test
Verander `serve_index()`/`serve_settings()` zodat `YOUR_API_KEY_HERE` runtime vervangen wordt door `CONFIG["api_key"]`. Dan werkt dashboard direct in Docker zonder `sed`.

### F2. Debounce DHCP misconfiguration warnings
Max 1x per 5 minuten per node loggen, of alleen bij state-change.

### F3. Fallback dhcp_leases bij geen MASTER
Als geen node MASTER is, tel leases van de node met `dhcp_enabled=True`.

### F4. DNS mock in mock_pihole.py
Voeg lightweight UDP DNS server toe (poort 53, antwoord altijd 1.2.3.4) zodat DNS checks slagen in Docker.

### F5. `/api/commands` endpoint implementeren
6 commands: `monitor_status`, `monitor_logs`, `keepalived_status`, `keepalived_logs`, `vip_check`, `db_recent_events`. Gebruik subprocess met timeout en output capture.

---

## 🔵 Verbeteringen — Documentatie & Tooling

### D1. LOCAL_SETUP.md herschrijven
Bijwerken naar huidige Docker setup: `10.99.0.x` subnet, fake clients, `docker compose` v2, geen Redis. Verwijs naar `make docker-up`.

### D2. Test coverage uitbreiden
**Huidige coverage:** 5% (141 tests, alleen parsing/validation). Ontbreekt: async operations, database, notifications, API handlers met echte HTTP.

### D3. HTTPS/reverse proxy setup documenteren
Nginx/Caddy voorbeeld voor productie HTTPS.

### D4. Documentatie taal standaardiseren
Mix van NL en EN in docs. Kies één taal.

---

## 🟣 pisen CLI Tool — Analyse

### Status: Bruikbaar maar beperkt
**Locatie:** `bin/pisen`

**Pluspunten:**
- Mooi gestructureerd met Colors, Config, Commands classes
- 6 handige subcommands: status, logs, vip, dashboard, health, test
- Auto-detect server type (monitor/pihole/unknown)
- Goede failover testing guide

**Problemen:**
- P1: Hardcoded pad naar VERSION: `/home/user/Workspace/pihole-sentinel/VERSION` (regel 402)
- P2: Vereist `systemctl` → werkt niet in Docker, alleen op productie
- P3: Geen API client modus (zou via HTTP naar monitor API kunnen praten)
- P4: Copyright hardcoded `2025` → moet dynamisch of `2025-2026`

**Aanbeveling:** Behouden en bijwerken. De CLI is nuttig voor productie. Voeg een `--api` modus toe die via HTTP naar de monitor API praat (werkt dan ook in Docker). Fix het hardcoded pad.

---

## 🐳 Docker Test Environment

### Huidige status (werkend)
- 17 containers: 2 mock Pi-holes, 1 monitor, 12 fake clients
- Elk Pi-hole ziet 15 DHCP leases (3 static + 12 ARP-discovered)
- 141 unit tests passen
- Mock Pi-holes met ARP auto-discovery

### Bekende Docker limitaties (verwacht, geen bugs)
- **dns: false** — mock piholes serveren geen echte DNS
- **Beide nodes BACKUP** — geen keepalived = geen VIP
- **Geen failover events** — zonder VIP wisseling geen MASTER switch
- **Dashboard 403** — API key niet geïnjecteerd (zie B9)

### Handige commando's
```bash
make docker-up        # Start volledige omgeving (17 containers)
make docker-down      # Stop + cleanup
make docker-status    # Status overview
make docker-failover  # Simuleer primary failure
make docker-recover   # Herstel primary
make docker-test      # Smoke tests
make docker-logs      # Live logs
```

---

## Voltooide Items (2026-02-06)
- [x] Repository cleanup: .gitignore, dode links, stale versies
- [x] Licentie gecorrigeerd: MIT → GPLv3 in alle bestanden
- [x] CHANGELOG.md structuur gefixed
- [x] CLAUDE.md verwijzingen naar niet-bestaande bestanden opgeschoond
- [x] Docker dev files (Dockerfile.dev, docker-compose.test.yml) aan git toegevoegd
- [x] tmp/ directory opgeruimd
- [x] docs/README.md geconsolideerd en geoptimaliseerd
- [x] Alle docs versienummers bijgewerkt naar 0.12.0-beta.7
- [x] Docker test environment uitgebreid met 12 fake clients
- [x] Mock Pi-hole ARP auto-discovery voor DHCP leases
- [x] `.dockerignore` toegevoegd
- [x] Makefile uitgebreid met docker-status/failover/recover targets
- [x] Full GUI audit (index.html + settings.html + alle API endpoints)
- [x] pisen CLI tool geaudit

---

**Laatste audit:** 2026-02-06
