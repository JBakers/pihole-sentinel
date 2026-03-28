# CLAUDE.md - AI Assistant Guide for Pi-hole Sentinel

**Last Updated:** 2026-03-28

**Version:** 0.12.4-beta.9

**Project:** Pi-hole Sentinel - High Availability for Pi-hole
**Audit Status:** ✅ Production Ready (Score: 89/100 - Excellent)

This document provides comprehensive guidance for AI assistants working with the Pi-hole Sentinel codebase. It covers architecture, structure, conventions, development workflows, and quality assurance.

> **📌 Planning & TODOs:** See **[PLAN.md](PLAN.md)** for the active development plan,
> all open tasks, bugs, and design decisions.
> This file (CLAUDE.md) is the **reference document** — PLAN.md is the **working document**.

**Recent Updates (v0.12.4, March 2026):**
- setup.py end-to-end deployment with preflight checks + automatic rollback
- Fault debounce + paired recovery notifications
- System Commands panel + ANSI colour rendering in dashboard
- Container architecture PoC on `feature/container-architecture` branch

---

## ⚠️ MANDATORY RULES - READ FIRST

### Critical: Never Commit Without User Confirmation (ALWAYS ASK FIRST)

**🚨 NEVER COMMIT OR PUSH CHANGES WITHOUT EXPLICIT USER APPROVAL 🚨**

#### Commit Protocol (REQUIRED)

**BEFORE making ANY commit, you MUST:**

1. ✅ **Show the user what you plan to commit** (changed files, reason, commit message)
2. ✅ **Wait for explicit confirmation** ("yes", "commit", "go ahead")
3. ✅ **Only commit after user confirms**

**No exceptions. Always ask before commit.**

---

### Critical: Development Environment Awareness (ALWAYS REMEMBER)

**🚨 WE WORK IN DIFFERENT ENVIRONMENTS - NEVER FORGET THIS 🚨**

- **AI** edits files directly via tools. **User** syncs via git.
- **GitHub** is the ONLY connection point between AI sandbox and user's machine.
- **NEVER** tell user to edit files in `/home/user/pihole-sentinel/` — make the changes yourself.
- **ALWAYS** push to GitHub, then tell user which branch to pull.

---

### Critical: Version Management (MUST FOLLOW FOR EVERY COMMIT)

**🚨 THESE RULES ARE NON-NEGOTIABLE AND MUST BE FOLLOWED FOR EVERY CODE CHANGE 🚨**

#### Version Update Requirements

**BEFORE making ANY commit, you MUST:**

1. ✅ **Update `VERSION` file** with new semantic version
2. ✅ **Update `CHANGELOG.md`** with detailed entry
   - Add entry under appropriate version section
   - Use categories: New, Improved, Fixed, Security, Documentation
   - Include specific details of what changed
3. ✅ **Update `CLAUDE.md` header** (lines 3-4) with new version and date

#### Semantic Versioning Rules (SemVer 2.0.0)

**This project STRICTLY adheres to [Semantic Versioning 2.0.0](https://semver.org/).**

Given a version number **MAJOR.MINOR.PATCH-PRERELEASE**, increment:

1. **MAJOR** version (X.0.0) when you make incompatible API changes or breaking changes
   - Example: Changing configuration file format without backward compatibility
   - Example: Removing or renaming required environment variables
   - Example: Changing CLI arguments or options

2. **MINOR** version (0.X.0) when you add functionality in a backward compatible manner
   - Example: Adding new features
   - Example: Adding new optional configuration options
   - Example: Significant changes like license changes (in beta context)

3. **PATCH** version (0.0.X) when you make backward compatible bug fixes
   - Example: Fixing bugs without changing functionality
   - Example: Performance improvements
   - Example: Security patches that don't change behavior

**Pre-Release Versioning (Beta Phase):**

We are currently in **beta** phase (0.x.x-beta.y). Version format: `MAJOR.MINOR.PATCH-beta.INCREMENT`

- **Minor bump (0.9.0 → 0.10.0):** Significant changes or features warranting new minor version
  - Each new minor gets `-beta.1` suffix
  - Example: `0.10.0-beta.1` (license change was significant enough for minor bump)

- **Beta increment (beta.1 → beta.2 → … → beta.10):** Changes within same minor version
  - Bug fixes: increment beta (e.g., `0.10.0-beta.1` → `0.10.0-beta.2`)
  - New features: increment beta (e.g., `0.10.0-beta.2` → `0.10.0-beta.3`)
  - **Maximum 10 betas per patch level** — after beta.10 bump PATCH and reset to beta.1
  - Example: `0.12.0-beta.10` → `0.12.1-beta.1` (not `0.12.0-beta.11`)
  - Keep same MINOR version unless change is truly significant

- **Major version 1.0.0:** Reserved for production-ready release
  - Will mark end of beta phase
  - Indicates stable, production-ready software
  - Only use when ready for public release

**Examples:**
```
0.9.0-beta.1   → Initial beta release
0.9.0-beta.2   → Bug fix in same series
0.10.0-beta.1  → Significant change (e.g., license change)
0.10.0-beta.2  → Bug fix after significant change
0.10.0-beta.10 → Max betas reached for 0.10.0
0.10.1-beta.1  → Next fix after max betas (patch bump, reset)
0.11.0-beta.1  → Next significant feature
1.0.0          → Production release (NO beta suffix)
```

**Quick Decision Tree:**
- 🔴 Breaking change? → Bump MAJOR (but stay in beta: use 0.X.0-beta.1)
- 🟡 Significant change or new feature series? → Bump MINOR, reset to beta.1
- 🟢 Bug fix or feature in current series? → Increment beta number
- ⚪ Documentation only? → No version change needed

#### Pre-Commit Verification Checklist

**AI Assistant: You MUST verify ALL items before executing `git commit`:**

- [ ] `VERSION` file updated
- [ ] `CHANGELOG.md` has new entry for this version
- [ ] `CLAUDE.md` header updated (line 4)
- [ ] No `print()` statements in Python code (use `logger.*()`)
- [ ] No hardcoded credentials or secrets
- [ ] All bash scripts use LF line endings (not CRLF)
- [ ] Commit message follows format: `type: description`

#### Commit Message Format (REQUIRED)

```
type: brief description (50 chars max)

Longer explanation if needed.
What changed and why.

Version: X.Y.Z
```

**Valid types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `security`

#### AI Assistant Failure Protocol

**If you (AI assistant) make a commit without updating VERSION and CHANGELOG.md:**
- ❌ You have FAILED this task
- ❌ The commit is INVALID
- ✅ You must immediately create a follow-up commit fixing the version
- ✅ Apologize to the user and explain what was missed

**No exceptions. No shortcuts. These rules apply to EVERY commit.**

---

### Critical: Always Push Changes (Git Workflow)

**🚨 NEVER END A SESSION WITHOUT PUSHING ALL CHANGES TO GITHUB 🚨**

- Commit all changes with proper message
- Push to the designated branch
- Verify push succeeded
- Inform user which branch to pull from

**Unpushed changes = LOST WORK.** If you forget to push, you have FAILED the task.

---

### Critical: NEVER Merge to Protected Branches (FOOLPROOF SAFEGUARD)

**🚨 AI AGENTS MAY ONLY COMMIT TO THE DEVELOP BRANCH 🚨**

**🚨 ONLY THE USER MAY MERGE TO TESTING/MAIN BRANCHES 🚨**

#### Merge Restrictions (ABSOLUTE)

**MANDATORY RULE - NO EXCEPTIONS:**

- ✅ AI agents may **ONLY** commit to the `develop` branch
- 🚫 AI agents may **NEVER** merge to the `testing` branch
- 🚫 AI agents may **NEVER** merge to the `main` branch
- 🚫 AI agents may **NEVER** push to the `testing` branch
- 🚫 AI agents may **NEVER** push to the `main` branch
- ✅ **Only the repository owner** may merge from `develop` → `testing` → `main`

**Enforcement:** Git hook `.githooks/pre-merge-commit` blocks all merges to `testing` and `main`.
Install hooks: `git config core.hooksPath .githooks`

**If you accidentally start a merge on a protected branch:**
1. `git merge --abort`
2. `git checkout develop`
3. Inform the user

**If user asks you to merge to testing/main:** Do NOT execute it. Provide the commands for them to run locally.

---

### Critical: Language — Dutch Communication, English Code (ALWAYS)

- **Communication with user:** ALWAYS in **Dutch** (answers, explanations, questions, error messages)
- **Code:** ALWAYS in **English** (variable/function names, comments, docstrings, log messages, UI text, API responses)
- **Documentation files (.md):** ALWAYS in **English**

---

### Required: Provide Git Commands for Learning

**🎓 ALWAYS SHOW GIT COMMANDS TO HELP USER LEARN 🎓**

**WHENEVER you use git, you MUST:**

1. ✅ **Show the exact command** in a code block
2. ✅ **Explain what it does** in simple terms
3. ✅ **Provide the pull command** user can run locally

**After EVERY push, provide the pull command for the user.**

**Show git commands for every operation so the user learns by example.**

---

## Project Overview

### What is Pi-hole Sentinel?

Pi-hole Sentinel is a High Availability (HA) solution for Pi-hole DNS servers that provides:

1. **Automatic Failover** - VIP (Virtual IP) switches automatically between Pi-holes using VRRP
2. **Real-time Monitoring** - Web dashboard with live status updates and historical data
3. **DHCP Failover** - Optional automatic DHCP activation/deactivation
4. **Smart Notifications** - Alerts via Telegram, Discord, Pushover, Ntfy, or webhooks
5. **Configuration Sync** - Built-in script to keep Pi-holes synchronized

### Key Features

- DNS failover (always enabled)
- Optional DHCP failover with misconfiguration detection
- Beautiful web dashboard (desktop & mobile responsive)
- Dark mode support
- Works alongside existing sync solutions (Nebula-sync, etc.)
- Automatic timezone detection and NTP synchronization
- SSH key-based authentication with automated setup

### System Requirements

- **Pi-hole Servers:** Pi-hole v6.0+, Debian/Ubuntu, static IPs
- **Monitor Server:** Any Linux (Debian/Ubuntu recommended), 512MB RAM, 1GB disk
- **Python:** 3.8+ (tested with 3.13)
- **Network:** All servers must be on the same subnet

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       Network Topology                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐         VIP          ┌──────────────┐    │
│  │  Primary     │◄─────(Keepalived)────►│  Secondary   │    │
│  │  Pi-hole     │                       │  Pi-hole     │    │
│  │              │      VRRP Protocol    │              │    │
│  │  + FTL       │                       │  + FTL       │    │
│  │  + Keepalived│                       │  + Keepalived│    │
│  └──────┬───────┘                       └───────┬──────┘    │
│         │                                       │           │
│         │            ┌──────────────┐           │           │
│         └────────────►   Monitor    ◄───────────┘           │
│                      │   Server     │                       │
│                      │              │                       │
│                      │  + FastAPI   │                       │
│                      │  + SQLite    │                       │
│                      │  + Dashboard │                       │
│                      └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

### How It Works

1. **Keepalived (VRRP)**
   - Runs on both Pi-holes
   - Manages Virtual IP (VIP) assignment
   - Monitors Pi-hole FTL service health
   - Handles DHCP failover (if enabled)
   - Uses priority-based master election (Primary: 150, Secondary: 100)

2. **Monitor Service (FastAPI)**
   - Polls both Pi-holes every 10 seconds
   - Checks: connectivity, Pi-hole service, VIP location, DNS resolution, DHCP status
   - Stores status history in SQLite database
   - Serves real-time web dashboard
   - Manages notification settings and delivery

3. **Health Check Flow**
   ```
   Monitor ─(TCP:80)──> Pi-hole 1 (Online?)
           ─(API)────> Pi-hole 1 (FTL Running?)
           ─(dig)────> Pi-hole 1 (DNS Working?)
           ─(API)────> Pi-hole 1 (DHCP Config?)
           ─(ARP)────> VIP (Who has VIP?)
   ```

4. **VIP Detection Method**
   - Creates TCP connections to VIP and both servers
   - Waits 200ms for ARP table to populate
   - Extracts MAC addresses from `ip neigh show`
   - Compares VIP MAC with both server MACs
   - Retries up to 3 times on failure

5. **Failover Process**
   ```
   Primary FTL Stops → Keepalived detects failure →
   Primary priority drops → Secondary becomes MASTER →
   VIP moves to Secondary → DHCP enabled on Secondary →
   DHCP disabled on Primary → Monitor detects change →
   Notification sent
   ```

### Container Architecture (Docker Sidecar Model)

> **Status:** In development on `feature/container-architecture` branch.
> See **[PLAN.md](PLAN.md)** for full plan and progress.

The new container architecture runs sentinel as a sidecar alongside each Pi-hole:

```
┌──────────────────────────────────────────────────────────┐
│                    Docker Network                         │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐     VIP: x.x.x.100  │
│  │  Pi-hole 1  │  │ Sentinel     │                      │
│  │  (DNS+DHCP) │◄─│ Node 1       │  ◄── MASTER          │
│  │  :80, :53   │  │ (keepalived  │      priority: 102   │
│  └─────────────┘  │  + sync agent│                      │
│                    │  :5000)      │                      │
│                    └──────────────┘                      │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐                      │
│  │  Pi-hole 2  │  │ Sentinel     │                      │
│  │  (DNS+DHCP) │◄─│ Node 2       │  ◄── BACKUP          │
│  │  :80, :53   │  │ (keepalived  │      priority: 101   │
│  └─────────────┘  │  + sync agent│                      │
│                    │  :5000)      │                      │
│                    └──────────────┘                      │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │  Monitor     │  │  Installer   │  ◄── WEB WIZARD     │
│  │  (Dashboard) │  │  (Wizard UI) │      :8888           │
│  │  :8080       │  │  :8888       │      (one-time use)  │
│  └──────────────┘  └──────────────┘                     │
└──────────────────────────────────────────────────────────┘
```

**Key components:**
- **sentinel-node** (`docker/sentinel-node/`) — Alpine container with keepalived + FastAPI sync agent
- **sync agent** (port 5000) — Endpoints: `/health`, `/state`, `/sync/gravity`, `/sync/status`
- **sentinel-installer** (`docker/sentinel-installer/`) — Web-based setup wizard (planned)
- **Keepalived VRRP** — Manages VIP failover between nodes (NET_ADMIN capability)
- **Sync token** — Peer-to-peer auth for gravity.db synchronization

**Sync Agent Endpoints:**

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/health` | GET | None | Health check |
| `/state` | GET | None | VRRP state (MASTER/BACKUP) |
| `/internal/state-change` | POST | Internal | Keepalived notify trigger |
| `/sync/gravity` | POST | Token | Push/pull gravity.db |
| `/sync/status` | GET | Token | Sync status overview |

---

## Codebase Structure

```
pihole-sentinel/
├── .git/                           # Git repository
├── .github/                        # GitHub workflows (if any)
├── dashboard/                      # Monitor service (FastAPI)
│   ├── monitor.py                 # Main monitoring service (FastAPI app)
│   ├── index.html                 # Dashboard UI
│   ├── settings.html              # Notification settings UI
│   └── .env.example              # Environment template
├── keepalived/                     # Keepalived configurations
│   ├── pihole1/                   # Primary node config templates
│   │   └── keepalived.conf
│   ├── pihole2/                   # Secondary node config templates
│   │   └── keepalived.conf
│   ├── scripts/                   # Health check & notification scripts
│   │   ├── check_pihole_service.sh    # FTL health check
│   │   ├── check_dhcp_service.sh      # DHCP health check
│   │   ├── dhcp_control.sh            # Enable/disable DHCP
│   │   ├── keepalived_notify.sh       # State transition handler
│   │   └── notify.sh                  # Send notifications
│   └── notify.conf.example        # Notification config template
├── systemd/                        # Systemd service files
│   ├── pihole-monitor.service     # Monitor service definition
│   ├── pihole-sync.service        # Sync service definition
│   └── pihole-sync.timer          # Sync timer (cron-like)
├── docker/                         # Docker container definitions
│   ├── sentinel-node/             # Production sidecar (keepalived + sync agent)
│   │   ├── Dockerfile
│   │   ├── entrypoint.sh
│   │   ├── requirements.txt
│   │   ├── keepalived/            # VRRP config templates + health checks
│   │   └── sync_agent/agent.py    # FastAPI sync agent
│   ├── sentinel-installer/        # Web-based installer wizard (planned)
│   ├── mock-pihole/               # Mock Pi-hole for testing
│   └── fake-client/               # Fake DHCP clients for testing
├── docker-compose.poc.yml          # PoC: 2 Pi-holes + 2 sentinel-nodes + VIP
├── docker-compose.test.yml         # Test: monitor + mock Pi-holes + clients
├── Dockerfile.dev                  # Dev image for monitor container
├── setup.py                        # Automated setup/deployment script (1480 lines)
├── sync-pihole-config.sh          # Configuration synchronization script
├── requirements.txt                # Main Python dependencies
├── system-requirements.txt         # System packages (apt/yum)
├── PLAN.md                         # 📌 Development plan & TODO tracking
├── docs/                           # Documentation directory
│   ├── README.md                  # Documentation index/navigation
│   ├── installation/
│   │   ├── quick-start.md        # Quick installation guide
│   │   └── existing-setup.md     # Add HA to existing Pi-holes
│   ├── maintenance/
│   │   └── sync.md               # Configuration synchronization
│   ├── development/
│   │   ├── README.md             # Development guide
│   │   └── testing.md            # User testing procedures
│   ├── api/
│   │   └── README.md             # API documentation
│   ├── configuration/            # (Future: config guides)
│   ├── usage/                    # (Future: usage guides)
│   └── troubleshooting/          # (Future: troubleshooting)
├── CHANGELOG.md                    # Version history
├── README.md                       # Project overview (concise, 410 lines)
├── LICENSE                         # GPLv3 License
├── VERSION                         # Current version (see file)
├── .gitignore                      # Git ignore rules
├── .markdownlint.json             # Markdown linting config
├── logo.svg                        # Project logo
├── logo-horizontal.svg            # Horizontal logo variant
└── social-preview.svg             # Social media preview image
```

### Directory Purposes

- **`dashboard/`** - Self-contained monitoring service with web UI
- **`docker/`** - Docker container definitions (sentinel-node, installer, mocks)
- **`keepalived/`** - Bare-metal VRRP failover logic and health checks
- **`systemd/`** - Service definitions for systemd
- **`tests/`** - Unit tests (pytest)
- **Root scripts** - Setup automation and synchronization

---

## Tech Stack

### Languages & Frameworks

- **Python 3.8+** (tested with 3.13)
  - FastAPI (≥0.104.0) - Web framework for monitoring API
  - Uvicorn (≥0.24.0) - ASGI server
  - aiohttp (≥3.9.0) - Async HTTP client for Pi-hole API
  - aiosqlite (≥0.19.0) - Async SQLite database
  - aiofiles (≥23.2.0) - Async file operations
  - python-dotenv (≥1.0.0) - Environment variable management
  - python-dateutil (≥2.8.2) - Date/time utilities

- **Bash** - Health checks, notifications, and sync scripts
- **HTML/CSS/JavaScript** - Dashboard and settings UI (vanilla JS, no frameworks)
- **SQL (SQLite)** - Status history and event storage

### System Dependencies

- **keepalived** - VRRP implementation for failover
- **arping** - ARP ping utility for network checks
- **iproute2** - Network configuration (`ip` command)
- **iputils-ping** - Connectivity tests
- **dnsutils** - DNS testing (`dig` command)
- **sqlite3** - Database for monitoring
- **sshpass** - SSH password authentication (for setup only)
- **build-essential, python3.11-dev** - Compiler toolchain for Python packages

### External APIs

- **Pi-hole v6 API**
  - `/api/auth` - Authentication (session.sid)
  - `/api/stats/summary` - Service statistics
  - `/api/config/dhcp` - DHCP configuration

- **Notification Services** (optional): Telegram Bot API, Discord Webhooks, Pushover API, Ntfy.sh, custom webhooks

---

## Key Conventions

### Python Code Style

1. **Logging over Print**
   - ALWAYS use `logger.info()`, `logger.debug()`, `logger.error()` instead of `print()`
   - Include `exc_info=True` for exception logging
   - Example:
     ```python
     try:
         result = await api_call()
     except Exception as e:
         logger.error(f"API call failed: {e}", exc_info=True)
     ```

2. **Async/Await Pattern**
   - Monitor service uses async extensively
   - Use `async def` for I/O operations
   - Use `aiohttp.ClientSession()` for HTTP calls
   - Use `aiosqlite` for database operations

3. **Type Hints** (preferred but not required)
   ```python
   async def check_pihole(ip: str, password: str) -> Dict[str, bool]:
       ...
   ```

4. **Error Handling**
   - Catch specific exceptions
   - Always log errors with context
   - Graceful degradation (continue monitoring even if one check fails)

5. **Configuration**
   - Environment variables via `python-dotenv`
   - Validate required vars at startup
   - Provide sensible defaults where possible

### Bash Script Style

1. **Shebang & Error Handling**
   ```bash
   #!/bin/bash
   set -e  # Exit on error (use with caution)
   ```

2. **Logging**
   - Timestamp all log entries
   - Use consistent log file paths (`/var/log/keepalived-notify.log`)
   - Example:
     ```bash
     timestamp() { date "+%Y-%m-%d %H:%M:%S"; }
     echo "$(timestamp) - Action performed" >> "$LOGFILE"
     ```

3. **Environment Variables**
   - Load from `.env` files where needed
   - Provide fallback defaults: `${INTERFACE:-eth0}`
   - Validate critical variables

4. **Line Endings**
   - ALWAYS use LF (Unix), never CRLF (Windows)
   - Setup script auto-converts with `sed -i 's/\r$//'`

### File Permissions

- **Configuration files with secrets:** `600` (root:root)
- **Application files:** `644` (service_user:service_user)
- **Executable scripts:** `755` (root:root)
- **Directories:** `755`

### Naming Conventions

- **Python files:** `snake_case.py` (e.g., `monitor.py`)
- **Bash scripts:** `kebab-case.sh` (e.g., `check-pihole-service.sh`)
- **Config files:** `lowercase.conf` or `.env`
- **HTML files:** `lowercase.html`

---

## Important Files Reference

### setup.py (1480 lines)

**Purpose:** Automated setup and deployment script

**Key Functions:**
- `SetupConfig` class - Main configuration manager
- `collect_network_config()` - Interactive network configuration
- `collect_dhcp_config()` - DHCP failover settings
- `setup_ssh_keys()` - Generate and distribute SSH keys
- `distribute_ssh_key()` - Copy SSH key to remote host
- `install_remote_dependencies()` - Install packages via SSH
- `configure_timezone_and_ntp()` - Auto-detect and set timezone
- `generate_configs()` - Generate keepalived and monitor configs
- `deploy_monitor_remote()` - Deploy monitor via SSH
- `deploy_keepalived_remote()` - Deploy keepalived via SSH
- `cleanup_sensitive_files()` - Securely delete generated configs

**Important Notes:**
- Requires root/sudo privileges
- Handles SSH key generation automatically
- Securely overwrites sensitive files before deletion
- Supports verbose mode with `--verbose` flag

### dashboard/monitor.py (FastAPI Service)

**Purpose:** Real-time monitoring and web dashboard

**Key Functions:**
- `init_db()` - Initialize SQLite schema
- `authenticate_pihole()` - Get Pi-hole API session
- `check_pihole_api()` - Check FTL service status
- `check_online()` - TCP connectivity check (port 80)
- `check_dns()` - DNS resolution test with `dig`
- `check_dhcp()` - Query DHCP configuration via API
- `check_who_has_vip()` - Determine VIP location via ARP
- `poll_status()` - Main polling loop (every 10 seconds)
- `get_status()` - Current status endpoint
- `get_history()` - Historical data endpoint

**API Endpoints:**
- `GET /` - Dashboard UI
- `GET /settings.html` - Settings UI
- `GET /api/status` - Current status JSON
- `GET /api/history?hours=24` - Historical data
- `GET /api/events?limit=50` - Event timeline
- `GET /api/notification_settings` - Notification config
- `POST /api/notification_settings` - Update notifications
- `POST /api/test_notification` - Test notification delivery

**Database Schema:**
```sql
status_history (
    id, timestamp, primary_state, secondary_state,
    primary_has_vip, secondary_has_vip,
    primary_online, secondary_online,
    primary_pihole, secondary_pihole,
    primary_dns, secondary_dns,
    dhcp_leases, primary_dhcp, secondary_dhcp
)

events (
    id, timestamp, event_type, message
)
```

### keepalived/scripts/keepalived_notify.sh

**Purpose:** Handle VRRP state transitions

**States:**
- `MASTER` - Node has VIP, enable DHCP, send gratuitous ARP
- `BACKUP` - Node lost VIP, disable DHCP
- `FAULT` - Node in fault state, disable DHCP

**Important:**
- Reads `$INTERFACE` from environment (no hardcoded `eth0`)
- Calls `dhcp_control.sh` to enable/disable DHCP
- Sends notifications via `notify.sh` (async)
- Logs to `/var/log/keepalived-notify.log`

### sync-pihole-config.sh

**Purpose:** Synchronize Pi-hole configurations between nodes

**Features:**
- Syncs: gravity.db, custom.list, adlists.list, DHCP leases, etc.
- Checks if remote file exists before rsync
- Distinguishes "file doesn't exist" vs "sync failed" errors
- Exits with error on critical failures

**Usage:**
```bash
# Manual sync
/usr/local/bin/sync-pihole-config.sh

# Automated via systemd timer
systemctl enable pihole-sync.timer
```

---

## Quick Commands

```bash
# Development
source venv/bin/activate    # Activate venv
make test                   # Run unit tests
make test-cov               # With HTML coverage report
make lint                   # Code quality checks
make format                 # Auto-format (black + isort)

# Docker test environment
make docker-up              # Start mock Pi-holes + clients
make docker-down            # Stop + cleanup
make docker-failover        # Simulate primary failure
make docker-recover         # Restore primary
make docker-status          # Status overview

# Production debugging
systemctl status pihole-monitor
journalctl -u pihole-monitor -f
tail -f /var/log/keepalived-notify.log
ip neigh show               # ARP table (VIP detection)
dig @<VIP> example.com      # Test DNS through VIP
sqlite3 /opt/pihole-monitor/monitor.db \
  "SELECT * FROM status_history ORDER BY timestamp DESC LIMIT 5;"
```

---

## Documentation Map

| Resource | Purpose |
|----------|----------|
| [README.md](README.md) | User-facing project overview + quick start |
| [PLAN.md](PLAN.md) | 📌 Active development plan, bugs, TODOs |
| [TODO_USER.md](TODO_USER.md) | Open bugs + improvement tracker |
| [CHANGELOG.md](CHANGELOG.md) | Full version history |
| [docs/installation/quick-start.md](docs/installation/quick-start.md) | Installation guide |
| [docs/installation/existing-setup.md](docs/installation/existing-setup.md) | Add HA to existing Pi-holes |
| [docs/development/testing.md](docs/development/testing.md) | Testing procedures + coverage plan |
| [docs/api/README.md](docs/api/README.md) | API documentation |
| [docs/maintenance/sync.md](docs/maintenance/sync.md) | Config sync |
| [.github/MERGE_FLOW.md](.github/MERGE_FLOW.md) | Git merge workflow diagram |

---

> **📌 See [PLAN.md](PLAN.md) for the active development plan, open bugs, and TODOs.**

**Last Updated:** 2026-03-28
**Maintainer:** JBakers
**Repository:** https://github.com/JBakers/pihole-sentinel
