# PLAN.md — Pi-hole Sentinel Development Plan

**Last Updated:** 2026-02-06
**Branch:** `feature/container-architecture`
**Base Version:** 0.12.0-beta.8
**Target Version:** 0.13.0-beta.1

> **📌 Dit is het centrale plannings- en TODO-document.**
> CLAUDE.md verwijst hiernaar. Alle openstaande taken, bugs, en het
> uitvoeringsplan staan hier. Houd dit bestand up-to-date bij elke sessie.

---

## Inhoudsopgave

- [Huidige Status](#huidige-status)
- [Architectuur Overzicht](#architectuur-overzicht)
- [Uitvoeringsplan](#uitvoeringsplan-7-fasen)
- [Openstaande Bugs](#openstaande-bugs)
- [Openstaande Verbeteringen](#openstaande-verbeteringen)
- [Lage Prioriteit / Later](#lage-prioriteit--later)
- [Voltooide Items](#voltooide-items)
- [Design Beslissingen](#design-beslissingen)
- [Referentie: Commando's](#referentie-commando's)

---

## Huidige Status

### Branch: `feature/container-architecture`

| Item | Status |
|------|--------|
| Keepalived sidecar PoC | ✅ Bewezen (VRRP election + VIP werkt in Docker) |
| Sentinel-node container | ✅ Werkend (keepalived + sync agent, FastAPI poort 5000) |
| docker-compose.poc.yml | ✅ 4 containers, VIP failover geverifieerd |
| Installer wizard | 🔲 Niet gestart (`docker/sentinel-installer/` is leeg) |
| Test environment unificatie | 🔲 Niet gestart |
| Documentatie bijgewerkt | 🔲 Niet gestart |

### Commits op deze branch (boven develop)

```
d294c34 style: formatting fixes (whitespace only)
616fb7d feat: sentinel-node container with keepalived + sync agent
769019e feat: keepalived container sidecar implementation (PoC)
```

---

## Architectuur Overzicht

### Huidige productie-architectuur (bare-metal)

```
┌──────────────┐       VIP        ┌──────────────┐
│  Primary     │◄──(Keepalived)──►│  Secondary   │
│  Pi-hole     │   VRRP Protocol  │  Pi-hole     │
│  + Keepalived│                  │  + Keepalived│
└──────┬───────┘                  └───────┬──────┘
       │         ┌──────────────┐         │
       └────────►│   Monitor    │◄────────┘
                 │   (FastAPI)  │
                 └──────────────┘
```

### Nieuwe container-architectuur (Docker sidecar model)

```
┌──────────────────────────────────────────────────────────┐
│                    Docker Network                         │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐     VIP: x.x.x.100  │
│  │  Pi-hole 1  │  │ Sentinel     │                      │
│  │  (DNS+DHCP) │◄─│ Node 1       │  ◄── MASTER         │
│  │  :80, :53   │  │ (keepalived  │      priority: 102   │
│  └─────────────┘  │  + sync agent│                      │
│                    │  :5000)      │                      │
│                    └──────────────┘                      │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐                      │
│  │  Pi-hole 2  │  │ Sentinel     │                      │
│  │  (DNS+DHCP) │◄─│ Node 2       │  ◄── BACKUP         │
│  │  :80, :53   │  │ (keepalived  │      priority: 101   │
│  └─────────────┘  │  + sync agent│                      │
│                    │  :5000)      │                      │
│                    └──────────────┘                      │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │  Monitor     │  │  Installer   │  ◄── WEB WIZARD     │
│  │  (Dashboard) │  │  (Wizard UI) │      :8888           │
│  │  :8080       │  │  :8888       │      (eenmalig)     │
│  └──────────────┘  └──────────────┘                     │
└──────────────────────────────────────────────────────────┘
```

### Installer Wizard Flow

```
Stap 1: Welkom        → "Heb je al Pi-holes?" (ja/nee)
Stap 2: Nodes         → IP, SSH user, auth methode per node (2-4)
Stap 3: Verificatie   → SSH test, Docker check, Pi-hole check
Stap 4: Docker Install→ Alleen als nodig (SSE progress)
Stap 5: Netwerk       → VIP IP, interface, VRRP auth, sync token
Stap 6: Review        → Overzicht + gegenereerde config preview
Stap 7: Deploy        → Realtime progress per node (SSE)
Stap 8: Verificatie   → VRRP election, VIP bereikbaar, sync ✅
```

---

## Uitvoeringsplan (7 Fasen)

### Fase 0: Voorbereiding & Cleanup

| # | Taak | Status | Details |
|---|------|--------|---------|
| 0.1 | Disk artifacts opruimen | 🔲 | `__pycache__/` (4x), `.pytest_cache/`, `htmlcov/`, `.coverage` |
| 0.2 | Redundante bestanden verwijderen | 🔲 | `dashboard/requirements.txt` (duplicaat), `dashboard/.env` (leeg) |
| 0.3 | keepalived-sidecar evalueren | 🔲 | `docker/keepalived-sidecar/` → vervangen door `sentinel-node`, verwijderen |
| 0.4 | Fix bug B6 | 🔲 | `CONFIG.get('primary_name')` → `CONFIG["primary"]["name"]` in monitor.py |
| 0.5 | Fix bug B9 | 🔲 | Runtime API key injection in Docker (niet hardcoded `YOUR_API_KEY_HERE`) |

### Fase 1: Installer Backend Skelet

| # | Taak | Status | Details |
|---|------|--------|---------|
| 1.1 | Dockerfile | 🔲 | `docker/sentinel-installer/Dockerfile` — Python 3.13-slim, paramiko, fastapi |
| 1.2 | requirements.txt | 🔲 | `fastapi`, `uvicorn`, `paramiko`, `docker>=7.0`, `pydantic` |
| 1.3 | main.py | 🔲 | FastAPI app, static files mount, health endpoint, lifespan handler |
| 1.4 | ssh_manager.py | 🔲 | paramiko SSH: test_connection, check_docker, install_docker, execute_command |
| 1.5 | docker_manager.py | 🔲 | Docker context create, deploy_stack, check_container_status, pull_images |
| 1.6 | config_generator.py | 🔲 | Genereer docker-compose.yml + .env per node (priority berekening) |

### Fase 2: Wizard API Endpoints

| # | Taak | Status | Details |
|---|------|--------|---------|
| 2.1 | Node configuratie | 🔲 | `POST /api/wizard/nodes` — ontvang IP, user, SSH credentials |
| 2.2 | SSH test | 🔲 | `POST /api/wizard/test-ssh` — test verbinding naar node |
| 2.3 | Docker check | 🔲 | `POST /api/wizard/check-docker` — controleer Docker op node |
| 2.4 | Docker install | 🔲 | `POST /api/wizard/install-docker` — installeer via `get.docker.com` (SSE) |
| 2.5 | Pi-hole check | 🔲 | `POST /api/wizard/check-pihole` — draait Pi-hole al? |
| 2.6 | Configuratie | 🔲 | `POST /api/wizard/configure` — VIP, DHCP, interface, etc. |
| 2.7 | Generatie | 🔲 | `POST /api/wizard/generate` — compose + env preview |
| 2.8 | Deployment | 🔲 | `POST /api/wizard/deploy` — deploy naar nodes (SSE progress) |
| 2.9 | Status | 🔲 | `GET /api/wizard/status` — deployment status alle nodes |
| 2.10 | Verificatie | 🔲 | `POST /api/wizard/verify` — VRRP + VIP + sync check |

### Fase 3: Wizard Frontend (Web UI)

| # | Taak | Status | Details |
|---|------|--------|---------|
| 3.1 | index.html wizard | 🔲 | 8-staps wizard, zelfde design als dashboard |
| 3.2 | CSS design tokens | 🔲 | Gradient `#667eea→#764ba2`, glassmorphism, dark mode |
| 3.3 | Vanilla JS wizard logic | 🔲 | fetch() API calls, EventSource SSE, stap-navigatie |
| 3.4 | Responsive layout | 🔲 | Mobile-friendly, `minmax(400px, 1fr)` grid |

### Fase 4: Docker Compose & Makefile

| # | Taak | Status | Details |
|---|------|--------|---------|
| 4.1 | docker-compose.installer.yml | 🔲 | Standalone compose voor installer (poort 8888) |
| 4.2 | Makefile targets | 🔲 | `installer-build`, `installer`, `installer-down` |

### Fase 5: Test Environment Consolidatie

| # | Taak | Status | Details |
|---|------|--------|---------|
| 5.1 | Nieuwe docker-compose.test.yml | 🔲 | Unified: mock Pi-holes + sentinel-nodes + monitor + clients |
| 5.2 | poc.yml verwijderen/archiveren | 🔲 | PoC bewezen, functionaliteit in test.yml |
| 5.3 | keepalived-sidecar verwijderen | 🔲 | Vervangen door sentinel-node |
| 5.4 | Makefile targets updaten | 🔲 | poc-* verwijderen, docker-* updaten, failover-test toevoegen |
| 5.5 | Dockerfile.dev updaten | 🔲 | Monitor container compatibel met sync agent endpoints |
| 5.6 | Fake clients terugbrengen | 🔲 | 12 → 4 clients (genoeg voor testing) |

### Fase 6: Tests, Documentatie & Versioning

| # | Taak | Status | Details |
|---|------|--------|---------|
| 6.1 | test_installer_api.py | 🔲 | Unit tests installer endpoints (mock SSH/Docker) |
| 6.2 | test_config_generator.py | 🔲 | Tests voor config generatie |
| 6.3 | Integration test script | 🔲 | `make integration-test`: deploy → failover → sync verify |
| 6.4 | VERSION bump | 🔲 | → `0.13.0-beta.1` |
| 6.5 | CHANGELOG.md update | 🔲 | Alle wijzigingen documenteren |
| 6.6 | README.md update | 🔲 | Container architectuur sectie |
| 6.7 | CLAUDE.md update | 🔲 | Header version, architectuur aanvullen |
| 6.8 | TODO_USER.md update | 🔲 | Afgevinkt + nieuwe items |

---

## Openstaande Bugs

### 🔴 Hoge Prioriteit

| ID | Bug | Locatie | Impact | Status |
|----|-----|---------|--------|--------|
| B1 | System Commands JS niet in `<script>` tag | `dashboard/index.html` ~L1090 | Commands sectie broken, JS zichtbaar als tekst | 🔲 |
| B2 | System Commands card in footer div genest | `dashboard/index.html` ~L1030 | Footer layout kapot | 🔲 |
| B3 | `/api/commands/{name}` endpoint ONTBREEKT | `dashboard/monitor.py` | Alle command buttons geven 404 | 🔲 |
| B4 | SnoozeResponse model mismatch → 500 | `dashboard/monitor.py` L182-186 | Snooze endpoint altijd 500 error | 🔲 |
| B5 | DHCP warning spam elke cycle | `dashboard/monitor.py` ~L1349 | Events overspoeld met dupes | 🔲 |
| B6 | CONFIG key mismatch in failover notificatie | `dashboard/monitor.py` ~L1305 | Notification variabelen zijn `None` | 🔲 **Fase 0** |

### 🟡 Medium Prioriteit

| ID | Bug | Locatie | Impact | Status |
|----|-----|---------|--------|--------|
| B7 | Duplicate "Monitor started" event | `dashboard/monitor.py` L201+1206 | Twee events bij herstart | 🔲 |
| B8 | `dhcp_leases` altijd 0 als geen MASTER | `dashboard/monitor.py` ~L1266 | 0 leases getoond | 🔲 |
| B9 | API key hardcoded als `YOUR_API_KEY_HERE` | `dashboard/index.html` + `settings.html` | Dashboard 403 in Docker | 🔲 **Fase 0** |
| B10 | LOCAL_SETUP.md compleet verouderd | `LOCAL_SETUP.md` | Misleidende docs | 🔲 |

> **Prioriteit voor dit plan:** B6 en B9 worden in Fase 0 gefixed (raken de installer/config pipeline).
> B1-B5, B7-B8, B10 staan gepland voor een aparte bugfix-sessie op `develop`.

---

## Openstaande Verbeteringen

| ID | Verbetering | Prioriteit | Status |
|----|-------------|------------|--------|
| F1 | API key runtime injection voor Docker | Medium | 🔲 (opgelost via B9 fix) |
| F2 | Debounce DHCP misconfiguration warnings | Medium | 🔲 |
| F3 | Fallback dhcp_leases bij geen MASTER | Low | 🔲 |
| F4 | DNS mock in mock_pihole.py (UDP:53) | Low | 🔲 |
| F5 | `/api/commands` endpoint implementeren | Medium | 🔲 (opgelost via B3 fix) |
| D1 | LOCAL_SETUP.md herschrijven | Medium | 🔲 |
| D2 | Test coverage uitbreiden (nu 5%) | High | 🔲 |
| D3 | HTTPS/reverse proxy docs | Low | 🔲 |
| D4 | Documentatie taal standaardiseren | Low | 🔲 |

---

## Lage Prioriteit / Later

| Taak | Details |
|------|---------|
| Onbeperkt nodes support (N > 4) | Dynamische priority berekening |
| Pi-hole deployment via installer | Voor users zonder bestaande Pi-holes |
| Monitor als container in stack | Dashboard automatisch mee-deployen |
| pisen CLI `--api` modus | HTTP client naar monitor API (werkt in Docker) |
| pisen hardcoded paths fixen | VERSION pad, copyright jaar |

---

## Voltooide Items

### Container Architecture Branch (6 feb 2026)

- [x] Keepalived sidecar PoC (VRRP election + VIP in Docker bewezen)
- [x] Sentinel-node container (keepalived + FastAPI sync agent)
- [x] docker-compose.poc.yml (2 mock Pi-holes + 2 sentinel-nodes)
- [x] Sync agent endpoints: `/health`, `/state`, `/sync/gravity`, `/sync/status`
- [x] Keepalived notify.sh → sync agent state-change trigger
- [x] Token-based auth voor sync communicatie

### Develop Branch (eerder voltooid)

- [x] Repository cleanup: .gitignore, dode links, stale versies
- [x] Licentie gecorrigeerd: MIT → GPLv3
- [x] Docker test environment (17 containers)
- [x] Mock Pi-hole met ARP auto-discovery
- [x] 12 fake clients voor DHCP lease testing
- [x] Full GUI audit (index.html + settings.html)
- [x] pisen CLI geaudit
- [x] 141 unit tests passing
- [x] Makefile met docker-*, poc-* targets

---

## Design Beslissingen

### Vastgelegd

| Beslissing | Keuze | Reden |
|------------|-------|-------|
| SSH library | `paramiko` | Meest stabiel, puur Python, breed gedocumenteerd |
| Wizard UI | Vanilla HTML/CSS/JS | Consistent met dashboard, geen frameworks |
| Template engine | f-strings / `str.format()` | Minimale dependencies, geen Jinja2 nodig |
| Progress streaming | SSE (Server-Sent Events) | Simpeler dan WebSockets, native `EventSource` JS |
| Max nodes (standaard) | 4 | Priority: 102, 101, 100, 99. Genoeg voor HA |
| Versie na voltooiing | `0.13.0-beta.1` | Minor bump: nieuwe feature module |
| keepalived-sidecar | Verwijderen | Volledig vervangen door sentinel-node |
| poc.yml | Opnemen in test.yml | PoC bewezen, unify test environments |
| Fake clients | 12 → 4 | Minder overhead, zelfde testwaarde |

### Design Tokens (van dashboard)

```css
/* Gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Glassmorphism cards */
background: rgba(226, 232, 240, 0.95);
backdrop-filter: blur(10px);
border: 1px solid rgba(203, 213, 225, 0.6);
border-radius: 16px;
box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);

/* Font stack */
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;

/* Colors */
--text-primary: #1e293b;
--text-secondary: #64748b;
--success: #10b981;
--error: #ef4444;
--warning: #f59e0b;
--info: #3b82f6;

/* Dark mode */
body.dark-mode background: linear-gradient(135deg, #1a1a2e, #16213e);
body.dark-mode .card: background: #0f3460;
body.dark-mode .text: #e9e9e9;

/* Borders & Radius */
--radius-card: 16px;
--radius-button: 8px;
--radius-badge: 20px;
```

---

## Referentie: Commando's

### Huidige branch hervat

```bash
git checkout feature/container-architecture
```

### PoC omgeving (huidige staat)

```bash
make poc          # Build + start (4 containers)
make poc-logs     # Live logs
make poc-down     # Stop + cleanup

# Test endpoints
curl http://localhost:5001/health   # Node 1 (MASTER)
curl http://localhost:5002/health   # Node 2 (BACKUP)
curl -H "X-Sync-Token: test-sync-token-12345" http://localhost:5001/sync/status
```

### Docker test omgeving (huidige staat)

```bash
make docker-up        # 17 containers
make docker-down      # Cleanup
make docker-status    # Overview
make docker-logs      # Live logs
make docker-failover  # Simuleer failure
make docker-recover   # Herstel
```

### Tests

```bash
make test             # Alle unit tests (141)
make test-cov         # Met coverage rapport
make lint             # Code quality
```

### Na voltooiing (nieuw)

```bash
make installer        # Build + start installer wizard
# → Browser: http://localhost:8888
make installer-down   # Stop installer

make integration-test # Full stack: deploy → failover → verify
```

---

**📌 Refereer vanuit CLAUDE.md naar dit bestand voor alle planning en TODO's.**
