# PLAN.md — Pi-hole Sentinel Development Plan

**Last Updated:** 2026-05-10
**Branch:** `develop`
**Current Version:** 0.19.0

> **📌 This is the central planning and TODO document.**
> CLAUDE.md references this file. All open tasks, bugs, and the
> development plan are tracked here. Keep this file up to date each session.

---

## Table of Contents

- [Current Status](#current-status)
- [Open Bugs](#open-bugs)
- [Open Improvements](#open-improvements)
- [Low Priority / Later](#low-priority--later)
- [Completed Items](#completed-items)
- [Command Reference](#command-reference)

---

## Current Status

### Branch: `develop` — v0.18.5

| Item | Status |
|------|--------|
| Core monitoring service (monitor.py) | ✅ Stable |
| Dashboard + Settings UI | ✅ Up to date |
| setup.py deployment (bare-metal) | ✅ Fully working (tested 2026-03-28) |
| Config sync (pihole.toml + gravity) | ✅ Stable |
| Notifications (Telegram/Discord/Pushover/Ntfy) | ✅ Working |
| System Commands panel | ✅ Working |
| Fault debounce + recovery notifications | ✅ Working |
| DHCP auto-detection | ✅ Working (3-poll debounce) |
| Docker integration test suite (20 tests) | ✅ Working (`make docker-integration`) |
| `pisen api` CLI command | ✅ Working (v0.18.0) |
| DNS latency health check | ✅ Working (v0.18.0, default 500ms) |
| Debug override mode (`DEBUG_MODE=true`) | ✅ Working (v0.18.0) |
| Unit tests | ⚠️ 55% monitor.py coverage (399 tests) — target 60%+ still open (see D2) |
| Container architecture (v2.0) | 🔲 Separate branch: `feature/container-architecture` |

---

## Open Bugs

No open bugs.

---

## Security & Best Practices Review — 2026-05-10

> Gegenereerd via volledige codebase-scan. Gesorteerd op kriticiteitsniveau.
> Elke fix is exact en actionable. Geen tutorials of algemene uitleg.

---

### 🔴 CRITICAL

---

**C1**
- **Level:** Critical
- **Location:** [setup.py](setup.py#L260) — ook L303, L307, L312, L681, L695, L736, L1482, L1955, L1963, L1969, L2376, L2378, L2380
- **Issue:** `StrictHostKeyChecking=no` in alle SSH/SCP-aanroepen gedurende installatie en remote commando's — staat MITM-aanvallen toe.
- **Fix:**
  ```python
  # Vervang in remote_exec, remote_copy, en alle andere ssh/scp calls:
  # VOOR (oud):
  "-o", "StrictHostKeyChecking=no",

  # NA (nieuw) — gebruik accept-new: accepteer bij eerste verbinding, weiger bij gewijzigde host key:
  "-o", "StrictHostKeyChecking=accept-new",
  "-o", "UserKnownHostsFile=/opt/pihole-monitor/.ssh/known_hosts",
  ```

---

**C2**
- **Level:** Critical
- **Location:** [docker/sentinel-node/sync_agent/agent.py](docker/sentinel-node/sync_agent/agent.py#L72)
- **Issue:** Wanneer `SYNC_TOKEN=""` (standaard), worden alle sync-endpoints volledig opengesteld zonder authenticatie; alleen een warning wordt gelogd.
- **Fix:**
  ```python
  def verify_sync_token(x_sync_token: str = Header(default="")):
      if not SYNC_TOKEN:
          # VOOR: logger.warning(...) + return  ← open!
          # NA: harde fout:
          raise HTTPException(status_code=503, detail="Sync token not configured — service unavailable")
      if not hmac.compare_digest(x_sync_token, SYNC_TOKEN):
          raise HTTPException(status_code=403, detail="Invalid sync token")
  ```

---

### 🟠 HIGH

---

**H1**
- **Level:** High
- **Location:** [dashboard/monitor.py](dashboard/monitor.py#L1260) — ook L1277, L1290, L1305, L1323
- **Issue:** Pi-hole API-communicatie (inclusief wachtwoordoverdracht) gebruikt onversleuteld HTTP (`http://{ip}/api/auth`).
- **Fix:**
  ```python
  # Voeg toe aan CONFIG (env-driven):
  "pihole_scheme": os.getenv("PIHOLE_SCHEME", "http"),  # zet op "https" voor TLS

  # Vervang in check_pihole_simple():
  scheme = CONFIG.get("pihole_scheme", "http")
  async with session.post(f"{scheme}://{ip}/api/auth", json={"password": password}, ...) as auth_resp:
  # Idem voor alle andere f"http://{ip}/..." aanroepen in die functie.
  ```

---

**H2**
- **Level:** High
- **Location:** [dashboard/monitor.py](dashboard/monitor.py#L2885) — ook L2988
- **Issue:** `test_notification`-endpoint roept `validate_webhook_url()` niet aan voor Discord- en Webhook-testpaden — SSRF-bescherming wordt omzeild.
- **Fix:**
  ```python
  # Voeg toe vóór de session.post() aanroep in service == 'discord' blok (L2885):
  if not validate_webhook_url(settings['webhook_url']):
      raise HTTPException(status_code=400, detail="Webhook URL is not allowed (SSRF protection)")

  # Voeg toe vóór de session.post() aanroep in service == 'webhook' blok (L2988):
  if not validate_webhook_url(settings['url']):
      raise HTTPException(status_code=400, detail="Webhook URL is not allowed (SSRF protection)")
  ```

---

**H3**
- **Level:** High
- **Location:** [dashboard/monitor.py](dashboard/monitor.py#L2871) — ook L2885, L2948, L2975, L2988
- **Issue:** `test_notification` maakt per aanroep een nieuw `aiohttp.ClientSession()` zonder timeout — resource-lek en kwetsbaar voor Slowloris.
- **Fix:**
  ```python
  # Vervang alle `async with aiohttp.ClientSession() as session:` in test_notification
  # door gebruik van de globale sessie met timeout:
  session = await get_http_session()
  # (verwijder de `async with aiohttp.ClientSession() as session:` wrapper per blok)
  # Voeg per post-aanroep een expliciete timeout toe:
  async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
  ```

---

### 🟡 MEDIUM

---

**M1**
- **Level:** Medium
- **Location:** [dashboard/monitor.py](dashboard/monitor.py#L330) — L330–L390
- **Issue:** `rate_limit_store` en `write_rate_limit_store` zijn onbegrensde `defaultdict`s; bij DoS met unieke IPs groeien ze onbeperkt in geheugen.
- **Fix:**
  ```python
  # Voeg toe aan de cleanup-stap in rate_limit_check en write_rate_limit_check,
  # vóór de append-stap, een max-cap op het aantal bijgehouden sleutels:
  MAX_TRACKED_IPS = 10_000

  async def rate_limit_check(request: Request):
      client_ip = _get_client_ip(request)
      now = datetime.now()
      rate_limit_store[client_ip] = [
          ts for ts in rate_limit_store[client_ip]
          if now - ts < timedelta(seconds=RATE_LIMIT_WINDOW)
      ]
      if len(rate_limit_store) > MAX_TRACKED_IPS:
          # Verwijder de oudste inactieve sleutels
          stale = [ip for ip, ts_list in rate_limit_store.items() if not ts_list]
          for ip in stale[:1000]:
              del rate_limit_store[ip]
      # ... rest ongewijzigd
  ```

---

**M2**
- **Level:** Medium
- **Location:** [dashboard/monitor.py](dashboard/monitor.py#L897)
- **Issue:** `Content-Security-Policy` header staat `'unsafe-inline'` toe voor `script-src`, wat XSS-bescherming significant verlaagt.
- **Fix:**
  ```python
  # Vervang in security_headers middleware:
  # VOOR:
  "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "

  # NA — gebruik een nonce (genereer per request):
  import secrets as _sec
  nonce = _sec.token_urlsafe(16)
  response.headers["Content-Security-Policy"] = (
      f"default-src 'self'; "
      f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
      "style-src 'self' 'unsafe-inline'; "
      "img-src 'self' data:; "
      "connect-src 'self'; "
      "frame-ancestors 'none'"
  )
  # Injecteer de nonce ook in de HTML via de serve_index/serve_settings handlers.
  ```

---

**M3**
- **Level:** Medium
- **Location:** [requirements.txt](requirements.txt)
- **Issue:** `packaging`-library wordt gebruikt in `_is_newer_version()` (monitor.py L1101) maar staat niet in `requirements.txt`; de fallback-vergelijking (`latest_clean > current_clean`) is lexicografisch en incorrect voor semantische versies.
- **Fix:**
  ```
  # Voeg toe aan requirements.txt:
  packaging>=23.0
  ```

---

**M4**
- **Level:** Medium
- **Location:** [dashboard/monitor.py](dashboard/monitor.py#L3249)
- **Issue:** `uvicorn.run(app, host="0.0.0.0")` is hardcoded — bind-adres is niet configureerbaar via omgevingsvariabele.
- **Fix:**
  ```python
  # Vervang de laatste regel:
  # VOOR:
  uvicorn.run(app, host="0.0.0.0", port=8080)

  # NA:
  uvicorn.run(
      app,
      host=os.getenv("BIND_HOST", "0.0.0.0"),
      port=int(os.getenv("BIND_PORT", "8080")),
  )
  ```

---

**M5**
- **Level:** Medium
- **Location:** [docker/sentinel-node/sync_agent/agent.py](docker/sentinel-node/sync_agent/agent.py)
- **Issue:** Geen rate limiting op enig endpoint in de sync agent; gezamenlijke endpoints zijn blootgesteld zonder throttling.
- **Fix:**
  ```python
  # Voeg toe als dependency (zelfde patroon als monitor.py write_rate_limit_check):
  from collections import defaultdict
  from datetime import datetime, timedelta
  _agent_rate_store = defaultdict(list)
  AGENT_RATE_LIMIT = 30
  AGENT_RATE_WINDOW = 60

  def agent_rate_limit(request: Request):
      ip = request.client.host if request.client else "unknown"
      now = datetime.now()
      _agent_rate_store[ip] = [t for t in _agent_rate_store[ip] if now - t < timedelta(seconds=AGENT_RATE_WINDOW)]
      if len(_agent_rate_store[ip]) >= AGENT_RATE_LIMIT:
          raise HTTPException(status_code=429, detail="Rate limit exceeded")
      _agent_rate_store[ip].append(now)

  # Voeg toe aan elke route: dependencies=[Depends(agent_rate_limit)]
  ```

---

### 🔵 LOW

---

**L1**
- **Level:** Low
- **Location:** [docker/mock-pihole/mock_pihole.py](docker/mock-pihole/mock_pihole.py#L45)
- **Issue:** Hardcoded standaard-testwachtwoord `"testpass123"` — indien mock server per ongeluk in productie draait, is het wachtwoord bekend.
- **Fix:**
  ```python
  # VOOR:
  PIHOLE_PASSWORD = os.getenv("PIHOLE_PASSWORD", "testpass123")

  # NA — geen default; verplicht via env:
  PIHOLE_PASSWORD = os.getenv("PIHOLE_PASSWORD", "")
  if not PIHOLE_PASSWORD:
      raise RuntimeError("PIHOLE_PASSWORD env var is required")
  ```

---

**L2**
- **Level:** Low
- **Location:** [dashboard/monitor.py](dashboard/monitor.py#L580) — ook L778, L808 en diverse API handlers
- **Issue:** `import json` wordt herhaaldelijk binnenin functies geïmporteerd terwijl het al module-breed beschikbaar is — overtollige microkosten en inconsistentie.
- **Fix:**
  ```python
  # Verwijder alle `import json` regels bínnen functies.
  # `json` staat al als top-level import (controleer: het staat NIET in de top imports!
  # Voeg eenmalig toe aan de module-level imports bovenaan monitor.py):
  import json
  ```

---

**L3**
- **Level:** Low
- **Location:** [dashboard/monitor.py](dashboard/monitor.py#L3042)
- **Issue:** `test_template_notification` heeft een dood-code-string `"""Test a template notification with sample data"""` als losse statement na de echte docstring — dead code.
- **Fix:**
  ```python
  # Verwijder regel 3042 volledig:
  """Test a template notification with sample data"""   # ← DELETE deze regel
  ```

---

**L4**
- **Level:** Low
- **Location:** [setup.py](setup.py#L1234)
- **Issue:** `subprocess.run(["sudo", "useradd", ...], check=False)` smoort fouten stil; mislukte systeemgebruiker-aanmaak blijft onopgemerkt.
- **Fix:**
  ```python
  # VOOR:
  subprocess.run(["sudo", "useradd", "-r", "-s", "/bin/false", "pihole-monitor"], check=False)

  # NA:
  result = subprocess.run(["sudo", "useradd", "-r", "-s", "/bin/false", "pihole-monitor"], capture_output=True)
  if result.returncode not in (0, 9):  # 9 = user already exists
      logger.warning(f"useradd failed (rc={result.returncode}): {result.stderr.decode().strip()}")
  ```

---

**L5**
- **Level:** Low
- **Location:** [dashboard/monitor.py](dashboard/monitor.py#L1451)
- **Issue:** `extract_mac` is een geneste functie die bij élke aanroep van `check_who_has_vip()` opnieuw wordt aangemaakt (per poll-cyclus).
- **Fix:**
  ```python
  # Verplaats extract_mac naar module-niveau (vóór check_who_has_vip):
  def _extract_mac(output: str) -> Optional[str]:
      """Extract MAC address from 'ip neigh show' output."""
      parts = output.split()
      try:
          lladdr_idx = parts.index('lladdr')
          return parts[lladdr_idx + 1].upper()
      except (ValueError, IndexError):
          return None
  ```

---

### ⚪ INFO

---

**I1**
- **Level:** Info
- **Location:** [dashboard/monitor.py](dashboard/monitor.py#L18)
- **Issue:** `import copy` wordt alleen gebruikt in `mask_sensitive_data()` (één `deepcopy`-aanroep) — geen probleem maar opvallend geïsoleerd.
- **Fix:** Geen actie vereist; optioneel `copy.deepcopy` vervangen door `json.loads(json.dumps(settings))` voor serialiseerbare dicts om de `copy`-import te elimineren.

---

**I2**
- **Level:** Info
- **Location:** [dashboard/monitor.py](dashboard/monitor.py#L2427) — ook L2330
- **Issue:** `open(config_path, 'w')` gevolgd door `os.chmod(config_path, 0o600)` heeft een TOCTOU-venster; bestand is tijdelijk world-readable bij aanmaak.
- **Fix:**
  ```python
  import stat

  def _open_secure(path: str):
      """Open bestand voor schrijven met mode 0o600 vanaf aanmaak."""
      fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
      return open(fd, 'w')

  # Vervang:
  with open(config_path, 'w') as f:
      json.dump(..., f, indent=2)
  os.chmod(config_path, 0o600)

  # Door:
  with _open_secure(config_path) as f:
      json.dump(..., f, indent=2)
  ```

---

## Open Improvements

| ID | Improvement | Priority |
|----|-------------|----------|
| D2 | Expand test coverage from 55% → 60%+ (monitor.py; focus: pushover/ntfy/webhook send paths, monitor_loop partial coverage, notification test endpoint) | Medium |

---

## Low Priority / Later

| Task | Details |
|------|---------|
| Prometheus metrics endpoint | `GET /metrics` in monitor.py |
| HTTPS / TLS support | Self-signed cert or Let's Encrypt integration |

| Database auto-cleanup | Delete status_history older than 30 days |

---

## Completed Items

### v0.18.5 (2026-04-21) — Bug fixes VIP check + keepalived buttons

- [x] VIP check showed "(not configured)" — `execute_command()` used flat keys, CONFIG is nested
- [x] Keepalived buttons visible on dedicated monitor server — fixed with `systemctl is-active` + `display: none`
- [x] Keepalived installed on monitor server — added `role` param to `install_remote_dependencies()`

### v0.18.0 (2026-04-21) — pisen api + DNS latency + debug mode

- [x] P3: `pisen api` command — fetch live status from monitor API over HTTP
- [x] DNS latency health check — measures response time, warning event if slow (default: 500ms)
- [x] Test/simulate-outage mode — `POST /api/debug/override` (gated: `DEBUG_MODE=true`)
- [x] P2: `pisen` copyright year dynamic — `2025-{current_year}` when year > 2025

### v0.16.8 (2026-04-15) — Security fixes

- [x] DHCP disabled on world-writable `.env`
- [x] Octal-safe IP validation in sync script
- [x] SSH known_hosts atomic updates
- [x] Defensive JSON parsing for notify_settings.json
- [x] SSH port respected for remote settings read

### v0.16.6 (2026-04-15) — Security audit + F4/D3

- [x] F4: UDP DNS mock — `build_dns_response()` serves real A-record replies on UDP:53
- [x] D3: HTTPS/reverse proxy documentation — Nginx + Caddy examples + `TRUST_PROXY_HEADERS` guidance in README
- [x] Security audit: `pisen` shell hardening, `curl --fail` in notify.sh, Docker root documentation
- [x] 3 new unit tests for DNS response builder, 2 new integration tests for DNS status
- [x] Testing guide refreshed (243 tests, 12 test files, coverage targets updated)

### v0.16.5 (2026-04-15) — Copilot PR review fixes

- [x] `StatusResponse` missing `dhcp_failover` field — added to Pydantic model
- [x] Rate limiter trusted `X-Forwarded-For` unconditionally — requires `TRUST_PROXY_HEADERS=true`
- [x] `setup.py` overwrote `notify_settings.json` on re-deploy — now merges, preserves notification config
- [x] SSH `known_hosts` blocked by `ReadOnlyPaths` in systemd unit — fixed (protect only private key)
- [x] `validate_ip` accepted invalid octets (e.g. 999.x.x.x) — added 0–255 range check
- [x] `DHCP_ENABLED` had no default in `keepalived_notify.sh` — default `true` for backward compat
- [x] Unconditional "Preserved" log messages in sync script — now gated on actual replacement
- [x] Unused `encoded_message` in `notify.sh` — removed dead curl encoding call
- [x] `requests` missing from `requirements-dev.txt` — added for integration tests

### v0.16.2 – v0.16.4 (2026-04-12 – 2026-04-15)

- [x] DHCP auto-detection disabled failover during Pi-hole outage (critical fix)
- [x] Docker integration test suite — 16 e2e tests via `make docker-integration`
- [x] `EVENT_DEBOUNCE_SECONDS` env var configurable (default: 30s)
- [x] DHCP failover default changed from `True` to `False`
- [x] `PiHoleStatus` Pydantic model missing stats fields (queries/blocked/clients)
- [x] Mock Pi-hole reset incomplete — state bleed between tests fixed

### v0.14.1 – v0.16.1 (2026-03-29 – 2026-04-12)

- [x] B1: Duplicate "Monitor started" event — fixed (single log point in monitor_loop)
- [x] B2: `dhcp_leases` always 0 when no MASTER — fallback `max()` of both nodes
- [x] B3: Dashboard API key hardcoded — runtime injection via `<meta>` tag
- [x] B10: LOCAL_SETUP.md completely outdated — rewritten for current Docker setup
- [x] F1: API key runtime injection — `serve_index`/`serve_settings` inject key via meta
- [x] F2: Fallback `dhcp_leases` when no MASTER — implemented
- [x] F5: `/api/commands` endpoint — 6 system commands implemented
- [x] P1: `pisen` CLI hardcoded VERSION path — fixed
- [x] pwhash / upstreams preservation via Python heredocs (no process arg exposure)
- [x] Section-scoped TOML sync (domain, cert, listeningMode)

### v0.12.5-beta.4 – v0.14.0 (2026-03-29)

- [x] SSH deployment with non-root user — all privileged remote commands now use `sudo`
- [x] `_s(user)` helper with `sudo -n` — fails fast instead of hanging without NOPASSWD
- [x] MITM warning printed when SSH keys are generated (StrictHostKeyChecking=no)
- [x] Config sync backup rotation fixed on secondary node (disk full bug)
- [x] `SYNC_MAX_BACKUPS` variable added (default: 3, configurable in sync.conf)

### v0.12.2 (2026-03-28)

- [x] setup.py fully working end-to-end (SSH + Pi-hole preflight checks)
- [x] Automatic rollback on deployment failure
- [x] Fault debounce 60s + paired recovery notifications
- [x] System Commands panel in dashboard
- [x] ANSI colour rendering in command output modal
- [x] Offline indicators (Pi-hole / VIP / DNS / DHCP)

### Earlier (develop branch)

- [x] Repository cleanup: .gitignore, dead links, stale versions
- [x] License corrected: MIT → GPLv3
- [x] Docker test environment (mock Pi-holes + fake clients)
- [x] 217 unit tests passing
- [x] Makefile with full development workflow
- [x] API key authentication on all endpoints
- [x] Rate limiting on all write endpoints
- [x] VIP detection retry logic (3×)

### Container Architecture (feature branch)

- [x] Keepalived sidecar PoC (VRRP election + VIP in Docker proven)
- [x] Sentinel-node container (keepalived + FastAPI sync agent on port 5000)
- [x] docker-compose.poc.yml (2 mock Pi-holes + 2 sentinel-nodes)
- [x] Sync agent endpoints: `/health`, `/state`, `/sync/gravity`, `/sync/status`

---

## Command Reference

### Development (local)

```bash
source venv/bin/activate
make test             # Run all unit tests
make test-cov         # With HTML coverage report (htmlcov/)
make lint             # Code quality checks
make format           # Auto-format with black + isort
```

### Docker test environment

```bash
make docker-up        # Start environment (mock Pi-holes + clients)
make docker-down      # Stop + cleanup
make docker-status    # Status overview
make docker-logs      # Live logs
make docker-failover        # Simulate primary failure
make docker-recover         # Restore primary
make docker-integration     # Run integration tests (requires docker-up)
```

### Container architecture PoC (feature branch)

```bash
git checkout feature/container-architecture
make poc              # Build + start (4 containers: 2 Pi-holes + 2 sentinel-nodes)
make poc-logs         # Live logs
make poc-down         # Stop + cleanup

# Test endpoints
curl http://localhost:5001/health
curl -H "X-Sync-Token: test-sync-token-12345" http://localhost:5001/sync/status
```

---

**📌 CLAUDE.md references this file for all planning and TODOs.**
