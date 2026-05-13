# PLAN.md — Pi-hole Sentinel Development Plan

**Last Updated:** 2026-05-13
**Branch:** `feature/multi-node-support`
**Current Version:** 0.20.1

> **📌 This is the central planning and TODO document.**
> CLAUDE.md references this file. All open tasks, bugs, and the
> development plan are tracked here. Keep this file up to date each session.

---

## Table of Contents

- [Integrated Action Plan (Copilot Reviews + TODOs)](#integrated-action-plan)
- [Current Status](#current-status)
- [Open Bugs](#open-bugs)
- [Open Improvements](#open-improvements)
- [Low Priority / Later](#low-priority--later)
- [Completed Items](#completed-items)
- [Command Reference](#command-reference)

---

## Integrated Action Plan (Copilot Reviews + TODOs)

### Summary: Next Steps (2026-05-13)

**Recent Copilot Review Fixes Completed (v0.18.1–0.18.2):**
- ✅ DNS latency response serialization in `/api/status` (v0.18.1)
- ✅ Debug override endpoint response codes + gating (v0.18.2)
- ✅ Async event loop refactor (`get_running_loop()` instead of `get_event_loop()`)

**Active Work (from commits 14fc333, d62b573):**
- ✅ Test coverage expanded to **54%** on monitor.py (339→399 tests, 17 files)
- ✅ Windows compatibility fixes for pytest

**Priority Queue (Next in Order):**

| Rank | ID  | Task | Status | Est. Effort | Blocker |
|------|-----|------|--------|-------------|---------|
| 1️⃣  | M1-P2 | Multi-node Phase 2 (API layer) | 🔲 Open | 2–3 days | M1-P1 ✅ |
| 2️⃣  | M1-P3 | Multi-node Phase 3 (Dashboard UI) | 🔲 Open | 2–3 days | M1-P2 |
| 3️⃣  | M1-P4 | Multi-node Phase 4 (Setup wizard) | 🔲 Open | 2–3 days | M1-P2 |
| 4️⃣  | D2  | Test coverage: 54% → **60%+** | 🔲 Open | 2–3 days | None |

---

### Session Handover (2026-05-13)

- ✅ **M1-P1 completed on `feature/multi-node-support`**
    - Task 1.1: Dynamic N-node config loading
    - Task 1.2: Normalized DB schema (`poll_cycles`, `node_status`) + migration
    - Task 1.3: Polling loop refactor to node list
    - Task 1.4: VIP detection generalized for node arrays
    - Task 1.5: Fault debounce generalized per node key
- ✅ **Docker test compose improved**
    - Added mock Pi-hole healthchecks in `docker-compose.test.yml` for reliable `service_healthy` dependencies
- ✅ **Validation status**
    - Full suite in current environment: `564 passed, 28 skipped`
    - Skips are environment-dependent (Docker not running and Windows chmod limitation)
- ➡️ **Next coding target**: Start M1-P2 API response migration (`/api/status`, `/api/history`) from primary/secondary shape to `nodes[]`

---

### D2 — Test Coverage: 54% → 60%+

**Current state:**
- `monitor.py` coverage: 54% (339→399 tests)
- Gaps identified: `monitor_loop` async flow, rate-limit middleware, API endpoints (`/api/history`, `/api/events`, `execute_command`)

**What needs testing:**
1. `monitor_loop()` full async flow (polling, debounce, notifications)
2. Rate-limit middleware (`rate_limit_check`, `write_rate_limit_check`)
3. API endpoints: `/api/history?hours=24`, `/api/events?limit=50`, `/api/commands`
4. Notification edge cases (retry, snooze expiry, service failures)
5. Error paths: network failures, malformed responses, timeouts

**Acceptance criteria:**
- [ ] Coverage reaches **60%+** on `monitor.py`
- [ ] `make test` passes with coverage report
- [ ] New tests in `tests/test_*.py` files (no missing imports, Windows-compatible)

---

### M1 — Multi-Node Support (Breaking Change)

**Planned for:** v1.0.0 (when 60% coverage achieved)
**Branch:** `feature/multi-node-support`
**Breaking change:** Yes (API format + config changes)

**Scope:** Convert 2-node hardcoding → N-node dynamic architecture

**Phases (sequential):**
1. **Phase 1:** Config + DB layer (environment vars, schema, internal data flow)
2. **Phase 2:** API layer (`/api/status`, `/api/history`, response models)
3. **Phase 3:** UI layer (dynamic node cards, charts)
4. **Phase 4:** Setup wizard (interactive N-node config)
5. **Phase 5:** Tests + Docker (fixtures, integration tests)

---

### Recent Copilot Review Fixes (v0.18.1–0.18.2, Already Completed ✅)

#### v0.18.1 (2026-04-21) — 6 Copilot Review Comments

**Issues Fixed:**
- ✅ DNS latency not exposed in `/api/status` — added `dns_latency_warn_ms` field to `StatusResponse` Pydantic model
- ✅ Dashboard hardcoded 500ms threshold → now uses `dns_latency_warn_ms` from server response
- ✅ Test-mode banner not hidden on non-2xx responses → added error handling in `index.html`
- ✅ Check DNS "restored" event fired incorrectly on failure/offline → fixed state logic in `check_dns()`
- ✅ Type annotation for `check_dns()` incomplete (`Tuple[bool, Optional[float]]`) → fixed
- ✅ Debug override applied unconditionally → gated behind `if DEBUG_MODE` check

**Commits:** `7f57ed0`, V0.18.1

#### v0.18.2 (2026-04-21) — 3 Copilot Review Comments

**Issues Fixed:**
- ✅ `dns_latency_warn_ms` field stripped from `/api/status` — added to model (not just internal)
- ✅ `/api/debug/override/status` returned 403 when DEBUG_MODE disabled → now returns 200 (prevents log noise)
- ✅ `asyncio.get_event_loop().time()` used in async functions → replaced with `get_running_loop().time()` (5 sites)

**Commits:** `4c4b39a`, v0.18.2

**Status:** All Copilot review comments have been resolved. No pending Copilot feedback.

---

---

## Current Status

### Branch: `feature/multi-node-support` — v0.20.1

| Item                                           | Status                                                         |
| ---------------------------------------------- | -------------------------------------------------------------- |
| Core monitoring service (monitor.py)           | ✅ Stable                                                      |
| Dashboard + Settings UI                        | ✅ Up to date                                                  |
| setup.py deployment (bare-metal)               | ✅ Fully working (tested 2026-03-28)                           |
| Config sync (pihole.toml + gravity)            | ✅ Stable                                                      |
| Notifications (Telegram/Discord/Pushover/Ntfy) | ✅ Working                                                     |
| System Commands panel                          | ✅ Working                                                     |
| Fault debounce + recovery notifications        | ✅ Working                                                     |
| DHCP auto-detection                            | ✅ Working (3-poll debounce)                                   |
| Docker integration test suite (18 tests)       | ✅ Working (`pytest tests/test_integration.py -m integration`) |
| `pisen api` CLI command                        | ✅ Working (v0.18.0)                                           |
| DNS latency health check                       | ✅ Working (v0.18.0, default 500ms)                            |
| Debug override mode (`DEBUG_MODE=true`)        | ✅ Working (v0.18.0)                                           |
| Unit tests                                     | ✅ 564 tests passing (28 skipped: env-dependent)                |
| M1-P1 (Multi-node Phase 1)                     | ✅ Completed on feature branch                                  |
| Container architecture (v2.0)                  | 🔲 Separate branch: `feature/container-architecture`           |

---

## Open Bugs

No open bugs.

---

## Security & Best Practices Review — 2026-05-10

> Status: alle bevindingen hieronder zijn geïmplementeerd in code en vastgelegd in commit `5216894`.
> Deze sectie blijft behouden als auditgeschiedenis; het is geen open todo-lijst meer.

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

| ID  | Improvement                                                                | Priority |
| --- | -------------------------------------------------------------------------- | -------- |
| M1-P2 | Multi-node API migration (`/api/status`, `/api/history` to `nodes[]`)     | High     |
| M1-P3 | Dashboard dynamic node rendering (remove hardcoded primary/secondary cards) | High     |
| M1-P4 | setup.py multi-node wizard/config generation                                | Medium   |
| M1-P5 | Multi-node test + docker fixtures                                           | Medium   |
| D2  | Expand test coverage (currently 54% monitor.py, target 60%+)               | Medium   |

---

## ✅ Completed Improvements (v0.18.0+)

| ID  | Improvement                                      | Completed |
| --- | ------------------------------------------------ | ---------- |
| P2  | `pisen` CLI: dynamic copyright year             | v0.18.0    |
| P3  | `pisen` CLI: `--api` mode (HTTP API client)     | v0.18.0    |

### M1 — Multi-Node Support (N Pi-holes)

> **Branch:** `feature/multi-node-support`
> **Breaking change:** Yes (API response format changes)
> **Scope:** Full stack refactor — config, DB, API, UI, setup wizard, tests

**Background:** The entire stack assumes exactly 2 nodes (`primary`/`secondary`). Every layer —
environment variables, DB schema, API responses, dashboard HTML, setup wizard, notifications —
hardcodes this two-node assumption. The sync agent (`sync_agent/agent.py`) is the **only**
component already N-aware (via `SYNC_PEERS`).

#### Phase 1 — Internal Data Layer _(blocks all other phases)_

- **Config format** (`dashboard/monitor.py`, `dashboard/.env.example`)
    - `PRIMARY_IP`/`SECONDARY_IP`/`PRIMARY_PASSWORD`/`SECONDARY_PASSWORD` →
      `PIHOLE_1_IP`, `PIHOLE_1_NAME`, `PIHOLE_1_PASSWORD`, ..., `PIHOLE_N_*`
    - `required_vars` validation becomes dynamic: detect `PIHOLE_1_*` up to first missing `PIHOLE_N_*`
    - `CONFIG` dict: `{"primary": {...}, "secondary": {...}}` → `{"nodes": [{...}, ...]}`

- **Database schema redesign** (`init_db()` in `monitor.py`)
    - Current: `status_history` with 12 hardcoded `primary_*`/`secondary_*` columns
    - New normalized schema:
        - `poll_cycles (id, timestamp, dhcp_leases)`
        - `node_status (id, poll_id FK, node_index, node_name, state, has_vip, online, pihole, dns, dhcp)`
    - Include migration strategy for existing databases

- **VIP detection** (`check_who_has_vip` in `monitor.py`)
    - Signature: `(vip, node_ips: list[str]) -> list[bool]` (was: `(vip, primary_ip, secondary_ip) -> (bool, bool)`)
    - Internally: `asyncio.gather(get_arp_entry(vip), *[get_arp_entry(ip) for ip in node_ips])`

- **Monitor loop** (`poll_status` / `monitor_loop`)
    - Replace all `primary_data`/`secondary_data` vars with `nodes_data: list[dict]` loop
    - `both_offline` → `all(not n["online"] for n in nodes_data)`
    - DHCP validation: `if nodes_data[i]["state"] == "MASTER" and not nodes_data[i]["dhcp"]: warn(...)`
    - Notification template vars: `{master_node, all_nodes: [...]}` instead of `{primary, secondary}`

- **Fault debounce** (`_check_fault_debounce`) — generalize 2-node checks to N nodes

#### Phase 2 — API Layer _(depends on Phase 1)_

- **`GET /api/status`** — Breaking change:
  `{primary: {...}, secondary: {...}}` → `{nodes: [{index, name, ip, state, has_vip, ...}], vip: ...}`
- **`GET /api/history`** — normalized per-node response format
- Update Pydantic/response models (`StatusResponse`, `PiHoleStatus`)

#### Phase 3 — Dashboard UI _(depends on Phase 2)_

- **Dynamic node cards** (`dashboard/index.html`) — remove hardcoded `#primary-card`/`#secondary-card`,
  JS loops over `data.nodes[]`
- **Failover chart** — N dynamic series per node with distinct colors
- Remove hardcoded labels like `'Primary (LXC)'` / `'Secondary (RPi)'`
- Generalize DHCP badges and event color logic

#### Phase 4 — Setup Wizard _(parallel with Phase 2/3)_

- **Interactive wizard** (`setup.py`) — ask "How many Pi-holes?" → loop N times for IP/name/password/SSH
- **Keepalived config generation** — generate N configs with descending priorities:
  node-0=150, node-1=140, node-2=130, ...
  Add `keepalived/node-N/keepalived.conf` alongside existing `pihole1/`/`pihole2/` templates
- **SSH mesh setup** (`_setup_cross_node_ssh`) — from A↔B to full N×(N-1) mesh

#### Phase 5 — Tests & Docker _(depends on all phases)_

- `tests/conftest.py` — `sample_config` fixture to `nodes: [...]` structure
- DB schema fixtures in `test_cleanup_db.py` and other test files
- `tests/test_integration.py` — `PRIMARY_URL`/`SECONDARY_URL` → `NODE_URLS: list`
- `docker-compose.test.yml` — add 3rd mock-pihole, monitor config to `PIHOLE_*` env vars
- `docker-compose.poc.yml` — add 3rd sentinel-node + pihole pair

#### Out of scope

- `docker/sentinel-node/sync_agent/agent.py` — already N-aware via `SYNC_PEERS`
- `keepalived/scripts/keepalived_notify.sh` — already per-node generic

#### Verification checklist

- [ ] `make test` passes after each phase
- [ ] `GET /api/status` with 3 configured nodes returns `nodes[]` array with 3 items
- [ ] Dashboard renders 3 node cards dynamically
- [ ] Keepalived node-3 wins VIP when nodes 1+2 fail
- [ ] DHCP misconfiguration warning appears correctly for node-3 as MASTER
- [ ] `make docker-integration` passes with 3-node scenario
- [ ] `setup.py` wizard completes correctly for 3 nodes

---

## Low Priority / Later

| Task                        | Details                                       |
| --------------------------- | --------------------------------------------- |
| Prometheus metrics endpoint | `GET /metrics` in monitor.py                  |
| HTTPS / TLS support         | Self-signed cert or Let's Encrypt integration |

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
