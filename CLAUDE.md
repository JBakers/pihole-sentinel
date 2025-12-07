# CLAUDE.md - AI Assistant Guide for Pi-hole Sentinel

**Last Updated:** 2025-12-07
**Version:** 0.11.0-beta.1
**Project:** Pi-hole Sentinel - High Availability for Pi-hole
**Audit Status:** ✅ Production Ready (Score: 89/100 - Excellent)

This document provides comprehensive guidance for AI assistants working with the Pi-hole Sentinel codebase. It covers architecture, structure, conventions, development workflows, and quality assurance.

**Recent Updates:**
- Comprehensive code audit completed (Nov 2025) - See `AUDIT_REPORT_20251116.md`
- Test automation infrastructure added - See `.github/TEST_AUTOMATION_GUIDE.md`
- Standardized test documentation templates - See `.github/TEST_DOCUMENTATION_TEMPLATE.md`

---

## ⚠️ MANDATORY RULES - READ FIRST

### Critical: Never Commit Without User Confirmation (ALWAYS ASK FIRST)

**🚨 NEVER COMMIT OR PUSH CHANGES WITHOUT EXPLICIT USER APPROVAL 🚨**

#### Commit Protocol (REQUIRED)

**BEFORE making ANY commit, you MUST:**

1. ✅ **Show the user what you plan to commit**
   - List all changed files
   - Explain what changed and why
   - Show the commit message you plan to use

2. ✅ **Wait for explicit confirmation**
   - User must say "yes", "commit", "go ahead", or similar
   - Do NOT assume silence means approval
   - Do NOT commit "automatically" because you think it's ready

3. ✅ **Only commit after user confirms**
   - User: "yes" → You may commit
   - User: asks questions → Answer, don't commit yet
   - User: silent → Wait, don't commit

**Examples:**

❌ **WRONG - Never do this:**
```
AI: "I've fixed the bug, let me commit that for you..."
AI: *commits without asking*
```

✅ **CORRECT - Always do this:**
```
AI: "I've fixed the bug. Here's what I changed:
     - dashboard/monitor.py (line 259): increased timeout to 10s
     - VERSION: 0.10.0-beta.11 → 0.10.0-beta.12
     - CHANGELOG.md: documented the fix

     Shall I commit these changes?"

User: "yes"
AI: *Now commits*
```

**Why This Rule Exists:**

- User wants control over what goes into git history
- User may want to review changes first
- User may want to adjust commit message
- User may want to make additional changes before committing
- Respects user's ownership of the repository

**No exceptions. Always ask before commit.**

---

### Critical: Development Environment Awareness (ALWAYS REMEMBER)

**🚨 WE WORK IN DIFFERENT ENVIRONMENTS - NEVER FORGET THIS 🚨**

#### Environment Separation

**AI Assistant (Claude) Environment:**
- Works in: `/home/user/pihole-sentinel/`
- Has direct file access via Read/Write/Edit tools
- Can execute bash commands in sandbox
- Makes all code changes directly
- **CANNOT** access user's local machine

**User's Local Environment:**
- Works in: `~/Workspace/pihole-sentinel/` (or similar local directory)
- Has NO access to `/home/user/pihole-sentinel/`
- Uses git to sync with GitHub repository
- Reviews and tests changes locally
- Performs git push/pull operations

**GitHub Repository:**
- Our **ONLY** connection/sync point
- Bridge between AI sandbox and user's local machine
- Single source of truth for code

#### Communication Rules (CRITICAL)

**❌ NEVER say:**
- "Please edit the file in `/home/user/pihole-sentinel/`"
- "Run this command in `/home/user/pihole-sentinel/`"
- "Create a file at `/home/user/pihole-sentinel/foo.txt`"
- "Navigate to `/home/user/pihole-sentinel/` and..."

**✅ ALWAYS say:**
- "I'll edit the file for you" (then use Edit tool)
- "I'll create this file" (then use Write tool)
- "Let me make these changes..." (then make changes directly)
- "After I commit and push, you can pull the changes locally"

#### Workflow Protocol

**AI Assistant's Role:**
1. Make file changes using Read/Write/Edit tools
2. Test changes if possible in sandbox
3. Update VERSION, CHANGELOG.md, and CLAUDE.md
4. Create git commit with proper message
5. Push to designated branch
6. **THEN** inform user: "Changes pushed to branch X, please pull locally to review"

**User's Role:**
1. Pull changes from GitHub: `git pull origin <branch>`
2. Review changes in `~/Workspace/pihole-sentinel/`
3. Test locally if needed
4. Provide feedback or approval
5. Merge to main branch (if applicable)

#### Example Correct Communication

**BAD (Don't do this):**
```
AI: "I've made the changes. Now please navigate to /home/user/pihole-sentinel/
     and run 'git commit -m "update"'"
```

**GOOD (Do this):**
```
AI: "I'll make these changes for you now..."
    [Uses Edit tool to modify files]
    [Uses Bash tool to git commit and push]
    "Done! I've committed and pushed the changes to branch claude/xyz.
     You can pull them locally with: git pull origin claude/xyz"
```

**This rule exists because this miscommunication happens frequently. Read it again before every response involving file operations.**

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

- **Beta increment (beta.1 → beta.2 → beta.3):** Changes within same minor version
  - Bug fixes: increment beta (e.g., `0.10.0-beta.1` → `0.10.0-beta.2`)
  - New features: increment beta (e.g., `0.10.0-beta.2` → `0.10.0-beta.3`)
  - Keep same MINOR version unless change is truly significant

- **Major version 1.0.0:** Reserved for production-ready release
  - Will mark end of beta phase
  - Indicates stable, production-ready software
  - Only use when ready for public release

**Examples:**
```
0.9.0-beta.1  → Initial beta release
0.9.0-beta.2  → Bug fix in same series
0.10.0-beta.1 → Significant change (e.g., license change)
0.10.0-beta.2 → Bug fix after significant change
0.10.0-beta.3 → New feature in same series
0.11.0-beta.1 → Next significant feature
1.0.0         → Production release (NO beta suffix)
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

#### Push Requirements

**BEFORE ending any work session, you MUST:**

1. ✅ **Commit all changes** with proper commit message
2. ✅ **Push to the designated branch** on GitHub
3. ✅ **Verify push succeeded** - check for errors
4. ✅ **Inform user** which branch to pull from

**Why This Rule Exists:**

- The AI sandbox (`/home/user/pihole-sentinel/`) is **temporary** and **isolated**
- User **CANNOT** access the sandbox directly
- GitHub is the **ONLY** way to transfer work from AI to user
- **Unpushed changes = LOST WORK** when sandbox closes

**Example Workflow:**

```bash
# ✅ CORRECT - Always push before ending session
git add .
git commit -m "feat: add new notification service"
git push -u origin claude/feature-xyz

# User is informed:
# "Changes pushed to branch claude/feature-xyz"
# "Pull locally with: git pull origin claude/feature-xyz"
```

**❌ NEVER do this:**
```bash
# Made changes, committed locally
git commit -m "feat: add feature"

# Ended session without pushing
# User: "Where are my changes?"
# AI: ❌ Lost forever in closed sandbox
```

#### Session End Checklist

**Before completing ANY task:**

- [ ] All files saved
- [ ] VERSION and CHANGELOG.md updated (if code changed)
- [ ] Changes committed with proper message
- [ ] **PUSHED to GitHub** ✅
- [ ] User informed of branch name
- [ ] User given pull command

**If you forget to push, you have FAILED the task.**

---

### Required: Provide Git Commands for Learning

**🎓 ALWAYS SHOW GIT COMMANDS TO HELP USER LEARN 🎓**

#### Command Transparency Rules

**WHENEVER you use git, you MUST:**

1. ✅ **Show the exact command** in a code block
2. ✅ **Explain what it does** in simple terms
3. ✅ **Provide the command user can run** locally (if applicable)

**Why This Rule Exists:**

- User wants to **learn git** through practice
- Seeing commands repeatedly builds **muscle memory**
- User can **replicate workflow** locally
- Transparency builds **understanding and trust**

#### Examples

**✅ GOOD - Educational approach:**

```markdown
I'll commit these changes now:

```bash
git add CLAUDE.md VERSION CHANGELOG.md
git commit -m "docs: add git workflow rules"
git push -u origin claude/feature-xyz
```

**What these commands do:**
- `git add` - Stage the modified files for commit
- `git commit -m` - Create a commit with the message
- `git push -u origin` - Push to GitHub and set upstream tracking

**To pull these changes locally:**
```bash
git pull origin claude/feature-xyz
```
```

**❌ BAD - No learning opportunity:**

```markdown
I've committed and pushed the changes.
```

#### Always Provide Pull Commands

**After EVERY push, provide the exact command:**

```bash
git pull origin <branch-name>
```

**Example:**
```
✅ Changes pushed to branch claude/docs-update-01abc

Pull locally with:
git pull origin claude/docs-update-01abc
```

#### Git Command Categories to Show

**Branch operations:**
```bash
git checkout -b claude/new-feature    # Create and switch to new branch
git branch                             # List all branches
git checkout testing                   # Switch to testing branch
```

**Staging and committing:**
```bash
git status                             # Check what changed
git add <file>                         # Stage specific file
git add .                              # Stage all changes
git commit -m "type: message"          # Commit with message
```

**Pushing and pulling:**
```bash
git push -u origin <branch>            # Push and set upstream
git pull origin <branch>               # Pull latest changes
git fetch origin                       # Fetch without merging
```

**Viewing history:**
```bash
git log --oneline -10                  # Last 10 commits
git show <commit-hash>                 # Show specific commit
git diff                               # Show unstaged changes
```

**This helps user learn git organically through repeated exposure.**

---

## Table of Contents

- [Mandatory Rules](#️-mandatory-rules---read-first)
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Codebase Structure](#codebase-structure)
- [Tech Stack](#tech-stack)
- [Development Environment Setup](#development-environment-setup)
- [Key Conventions](#key-conventions)
- [Important Files Reference](#important-files-reference)
- [Development Workflows](#development-workflows)
- [Testing Guidelines](#testing-guidelines)
- [Code Quality & Audit](#code-quality--audit)
- [Deployment Process](#deployment-process)
- [Common Pitfalls](#common-pitfalls)
- [Security Considerations](#security-considerations)

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
│   ├── .env.example              # Environment template
│   └── requirements.txt          # Dashboard-specific Python deps
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
├── setup.py                        # Automated setup/deployment script (1480 lines)
├── sync-pihole-config.sh          # Configuration synchronization script
├── requirements.txt                # Main Python dependencies
├── system-requirements.txt         # System packages (apt/yum)
├── CHANGELOG.md                    # Version history
├── README.md                       # User-facing documentation
├── DEVELOPMENT.md                  # Development guide
├── EXISTING-SETUP.md              # Guide for existing Pi-hole setups
├── SYNC-SETUP.md                  # Configuration sync guide
├── LICENSE                         # MIT License
├── VERSION                         # Current version (0.8.0)
├── .gitignore                      # Git ignore rules
├── .markdownlint.json             # Markdown linting config
├── logo.svg                        # Project logo
├── logo-horizontal.svg            # Horizontal logo variant
└── social-preview.svg             # Social media preview image
```

### Directory Purposes

- **`dashboard/`** - Self-contained monitoring service with web UI
- **`keepalived/`** - All VRRP failover logic and health checks
- **`systemd/`** - Service definitions for systemd
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

- **Notification Services** (optional)
  - Telegram Bot API
  - Discord Webhooks
  - Pushover API
  - Ntfy.sh
  - Custom webhooks (JSON POST)

---

## Development Environment Setup

### Prerequisites

- Linux system (Debian/Ubuntu recommended)
- Python 3.8+ installed
- Git
- Basic understanding of networking (IP addresses, VIP, VRRP)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/JBakers/pihole-sentinel.git
cd pihole-sentinel

# Create virtual environment (REQUIRED for Python 3.13+)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r dashboard/requirements.txt

# Verify installation
python -c "import fastapi, uvicorn, aiohttp; print('✓ All imports OK')"
```

### Environment Variables

Create `.env` file in `dashboard/` directory:

```bash
# Copy example
cp dashboard/.env.example dashboard/.env

# Edit with your values
nano dashboard/.env
```

Required variables:
```env
PRIMARY_IP=10.10.100.10
PRIMARY_NAME="Primary Pi-hole"
PRIMARY_PASSWORD=your_pihole_password

SECONDARY_IP=10.10.100.20
SECONDARY_NAME="Secondary Pi-hole"
SECONDARY_PASSWORD=your_pihole_password

VIP_ADDRESS=10.10.100.2
CHECK_INTERVAL=10
DB_PATH=/tmp/test.db  # For development
```

### Running Monitor Locally

```bash
source venv/bin/activate
cd dashboard
python monitor.py

# Access at http://localhost:8000
```

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

## Development Workflows

### Initial Development Setup (REQUIRED)

**Before making any commits, install the git pre-commit hook:**

```bash
# Option 1: Copy hook to .git/hooks (Recommended)
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Option 2: Configure git to use .githooks directory
git config core.hooksPath .githooks
```

**What the pre-commit hook does:**
- ✅ Enforces VERSION file updates for code changes
- ✅ Enforces CHANGELOG.md updates for code changes
- ✅ Checks for `print()` statements in Python files
- ✅ Checks for CRLF line endings in bash scripts
- ✅ Allows documentation-only changes without version updates

**Testing the hook:**
```bash
# Make a test change
echo "# test" >> dashboard/monitor.py
git add dashboard/monitor.py

# Try to commit without updating VERSION (should fail)
git commit -m "test: should fail"

# Expected output:
# ✗ ERROR: VERSION file not updated!
# ✗ ERROR: CHANGELOG.md not updated!
```

See `.githooks/README.md` for more details.

### Making Changes to Monitor Service

1. **Activate virtual environment**
   ```bash
   source venv/bin/activate
   ```

2. **Edit `dashboard/monitor.py`**
   - Use logging instead of print statements
   - Follow async/await patterns
   - Update database schema if needed

3. **Test locally**
   ```bash
   cd dashboard
   # Create test .env with dummy data
   python monitor.py
   # Visit http://localhost:8000
   ```

4. **Syntax check**
   ```bash
   python3 -m py_compile dashboard/monitor.py
   ```

5. **Commit changes**
   ```bash
   git add dashboard/monitor.py
   git commit -m "fix: improve error handling in VIP detection"
   ```

### Making Changes to Keepalived Scripts

1. **Edit script in `keepalived/scripts/`**
   - Maintain consistent logging format
   - Use environment variables (not hardcoded paths)
   - Test error conditions

2. **Check syntax**
   ```bash
   bash -n keepalived/scripts/keepalived_notify.sh
   ```

3. **Test on actual Pi-hole (staging environment)**
   ```bash
   # Copy to Pi-hole
   scp keepalived/scripts/keepalived_notify.sh root@pihole1:/usr/local/bin/

   # Test manually
   ssh root@pihole1 '/usr/local/bin/keepalived_notify.sh MASTER'

   # Check logs
   ssh root@pihole1 'tail -f /var/log/keepalived-notify.log'
   ```

### Adding New Features

1. **Update CHANGELOG.md**
   - Add entry under appropriate version
   - Use semantic versioning
   - Categorize: New, Improved, Fixed, Security, Documentation

2. **Update VERSION file** (if bumping version)
   ```bash
   echo "0.9.0" > VERSION
   ```

3. **Update README.md** (if user-facing changes)

4. **Test deployment end-to-end**
   - Test `setup.py` in staging environment
   - Verify all services start correctly
   - Test failover scenarios

### Updating Dependencies

1. **Review security advisories**
   ```bash
   pip list --outdated
   ```

2. **Update `requirements.txt`**
   ```bash
   # Use version constraints
   fastapi>=0.104.0  # Not ==0.104.0
   ```

3. **Test compatibility**
   ```bash
   pip install --upgrade -r requirements.txt
   python dashboard/monitor.py  # Verify no breaking changes
   ```

4. **Document in CHANGELOG.md**

---

## Testing Guidelines

### Testing Infrastructure Overview

Pi-hole Sentinel has a comprehensive testing infrastructure with automated scripts, standardized documentation templates, and continuous testing workflows.

**Key Testing Resources:**
- **`.github/TESTING_TODO.md`** - Complete testing checklist for `testing` branch (296 items)
- **`.github/TEST_DOCUMENTATION_TEMPLATE.md`** - Standardized test report template (802 lines)
- **`.github/TEST_AUTOMATION_GUIDE.md`** - Test automation guide with scripts (700 lines)
- **`.github/workflows/code-quality.yml`** - Automated CI/CD quality checks

### Testing Workflow

**For `testing` Branch:**

1. **Start New Test Cycle:**
   ```bash
   git checkout testing
   cp .github/TEST_DOCUMENTATION_TEMPLATE.md .github/test-reports/TEST_REPORT_$(date +%Y%m%d).md
   ```

2. **Run Automated Tests:**
   ```bash
   bash .github/scripts/run-syntax-checks.sh
   bash .github/scripts/run-quality-checks.sh
   bash .github/scripts/run-security-scans.sh
   bash .github/scripts/test-failover.sh <VIP> <primary_ip> <secondary_ip>
   bash .github/scripts/test-dashboard.sh <monitor_ip> <api_key>
   ```

3. **Execute Manual Tests:**
   - Follow checklist in `.github/TESTING_TODO.md`
   - Document results in test report
   - Take screenshots for visual tests

4. **Generate Test Summary:**
   ```bash
   bash .github/scripts/generate-test-summary.sh .github/test-reports/TEST_REPORT_$(date +%Y%m%d).md
   ```

### Unit Testing (Planned - HIGH PRIORITY)

**Status:** Not yet implemented
**Priority:** 🔴 HIGH (per audit recommendations)
**Target:** 60%+ code coverage

**Planned Test Coverage:**
- Input validation functions (`validate_ip`, `validate_interface_name`, etc.)
- VIP detection logic (`check_who_has_vip`)
- API request/response handling (`check_pihole_simple`)
- DHCP configuration parsing
- Error handling paths

**Framework:** pytest + pytest-asyncio for async tests

### Integration Testing

**Automated Tests Available:**
- Syntax validation (Python, Bash)
- Code quality checks (print statements, line endings, required files)
- Security scans (hardcoded secrets, file permissions)
- Failover testing (VIP transition, DNS continuity)
- Dashboard API testing (endpoints, response validation)

**Manual Tests Required:**
- Multi-platform deployment (Debian 11/12, Ubuntu 22.04/24.04, Raspberry Pi OS)
- Browser compatibility (Chrome, Firefox, Safari, Edge, mobile browsers)
- Long-running stability tests (7+ days)
- Load testing (1000+ queries/second)
- Network condition tests (latency, packet loss)

### Testing Commands

**Quick Health Checks:**
```bash
# Check monitor service
systemctl status pihole-monitor
journalctl -u pihole-monitor -f

# Check keepalived
systemctl status keepalived
journalctl -u keepalived -f
tail -f /var/log/keepalived-notify.log

# Check VIP location
ip addr show | grep <VIP>
arping -c 1 <VIP>

# Query database
sqlite3 /opt/pihole-monitor/monitor.db "SELECT * FROM status_history ORDER BY timestamp DESC LIMIT 5;"

# Test DNS
dig @<VIP> example.com

# Simulate failure
systemctl stop pihole-FTL  # On current MASTER
# Watch VIP move to other node
systemctl start pihole-FTL  # Restore
```

**Automated Test Execution:**
```bash
# Full test suite
cd .github/scripts
./run-all-tests.sh

# Individual test categories
./run-syntax-checks.sh
./run-quality-checks.sh
./run-security-scans.sh
./test-failover.sh 10.10.100.2 10.10.100.10 10.10.100.20
./test-dashboard.sh 10.10.100.30 $API_KEY
```

**Continuous Testing (Nightly):**
```bash
# Add to crontab for nightly testing
0 2 * * * /path/to/.github/scripts/nightly-tests.sh >> /var/log/pihole-sentinel-tests/nightly-$(date +\%Y\%m\%d).log 2>&1
```

### Test Sign-Off Criteria

Before merging `testing` → `main`:

- [ ] All automated tests pass (syntax, quality, security)
- [ ] Manual integration tests completed
- [ ] Performance meets requirements (failover < 5s, DNS disruption < 3s)
- [ ] No critical or high-severity bugs
- [ ] Security audit completed (no vulnerabilities)
- [ ] Documentation verified and accurate
- [ ] At least 7 days of stable operation in testing environment
- [ ] Browser compatibility confirmed
- [ ] Test pass rate ≥ 95%

See `.github/TESTING_TODO.md` for complete checklist.

---

## Code Quality & Audit

### Latest Audit Results (November 2025)

**Overall Assessment:** ✅ **PRODUCTION READY**
**Overall Score:** 89/100 (Excellent)
**Audit Report:** See `AUDIT_REPORT_20251116.md` for complete details

| Category | Score | Status |
|----------|-------|--------|
| Security | 95/100 | ✅ Excellent |
| Code Quality | 90/100 | ✅ Excellent |
| Testing | 60/100 | ⚠️ Needs Work |
| Documentation | 95/100 | ✅ Outstanding |
| Architecture | 95/100 | ✅ Excellent |
| Performance | 90/100 | ✅ Excellent |
| Operations | 90/100 | ✅ Excellent |
| Deployment | 95/100 | ✅ Excellent |

### Key Strengths (Audit Findings)

**Security (95/100):**
- ✅ API key authentication on all sensitive endpoints
- ✅ Comprehensive input validation (SQL injection prevention)
- ✅ Secure password handling (environment vars, immediate cleanup)
- ✅ SSH key automation (Ed25519)
- ✅ Proper file permissions (600 for secrets, 755 for scripts)
- ✅ Secure file deletion (overwrite with random data before deletion)
- ✅ Parameterized SQL queries throughout
- ✅ Rate limiting on notification test endpoint

**Code Quality (90/100):**
- ✅ All syntax checks pass (Python & Bash)
- ✅ Proper logging (no print() in monitor.py)
- ✅ Consistent naming conventions
- ✅ Comprehensive error handling
- ✅ LF line endings (Unix style)
- ✅ 3,360 lines of production code
- ✅ Clean separation of concerns

**Documentation (95/100):**
- ✅ 4,125+ lines of documentation
- ✅ 10 comprehensive guides (README, CLAUDE, DEVELOPMENT, etc.)
- ✅ Multiple user personas covered
- ✅ Well-structured and maintained

### Priority Recommendations (Audit Findings)

**🔴 HIGH PRIORITY:**

1. **Add Unit Tests** (Impact: Prevents regressions, improves quality)
   - Create `tests/` directory with pytest framework
   - Test critical functions (validate_ip, check_who_has_vip, etc.)
   - Target: 60%+ code coverage
   - Effort: Medium (2-3 weeks)

2. **Document CORS Configuration** (Impact: Enables remote dashboard access)
   - Update README.md with CORS setup for remote access
   - Add monitor IP to CORS whitelist instructions
   - Effort: Low (1 hour)

3. **Add Integration Tests** (Impact: Validates end-to-end functionality)
   - Docker-based test environment
   - Automated deployment tests
   - Failover scenario tests
   - Effort: High (5-7 days)

**🟡 MEDIUM PRIORITY:**

4. **Add HTTPS Support** (Impact: Improves security for remote access)
   - Self-signed certificates or Let's Encrypt integration
   - Reverse proxy documentation (nginx/traefik)
   - Effort: Medium (2-3 days)

5. **Add Database Cleanup Task** (Impact: Prevents database growth)
   - Auto-delete old status_history (>30 days)
   - Auto-delete old events (>90 days)
   - Effort: Low (2-3 hours)

6. **Create API Documentation** (Impact: Improves developer experience)
   - Create `API.md` with OpenAPI specification
   - Add request/response examples
   - Document error codes
   - Effort: Low (2-3 hours)

**🟢 LOW PRIORITY:**

7. **Add Prometheus Metrics** (Impact: Better monitoring integration)
8. **Add More Docstrings** (Impact: Improves code maintainability)
9. **Upgrade VRRP to AH Authentication** (Impact: Slightly better security)

### Code Quality Standards

**Python Code:**
- Use `logger.*()` instead of `print()` (except in setup.py for user interaction)
- Follow async/await patterns for I/O operations
- Use type hints where beneficial
- Add docstrings to all public functions
- Use parameterized SQL queries (never string concatenation)
- Handle exceptions with `exc_info=True` for stack traces

**Bash Scripts:**
- Use `set -e` for critical scripts
- Provide fallback defaults for environment variables
- Use LF line endings (never CRLF)
- Add timestamp to log entries
- Validate critical inputs
- Use proper exit codes (0 = success, 1 = failure)

**File Permissions:**
- Sensitive files (with secrets): `600` (root:root or service user)
- Configuration files: `644` (root:root)
- Executable scripts: `755` (root:root)
- Directories: `755`

### Automated Quality Checks

**CI/CD Pipeline (`.github/workflows/code-quality.yml`):**
- ✅ Python syntax and linting (Black, Flake8, Pylint)
- ✅ Bash syntax and linting (ShellCheck)
- ✅ Markdown linting (markdownlint)
- ✅ Security scanning (Bandit, Safety)
- ✅ File structure checks (secrets, line endings, required files)

**Local Quality Checks:**
```bash
# Run all quality checks locally
python3 -m py_compile dashboard/monitor.py setup.py
bash -n keepalived/scripts/*.sh sync-pihole-config.sh
shellcheck keepalived/scripts/*.sh sync-pihole-config.sh
```

### Risk Assessment

**Security Risk:** LOW
- No critical vulnerabilities found
- Secure coding practices followed
- Regular security updates

**Stability Risk:** LOW
- Robust error handling
- Graceful degradation
- Comprehensive logging

**Maintainability Risk:** LOW
- Excellent documentation
- Clean code structure
- Consistent conventions

**Operational Risk:** LOW
- Automated deployment
- Backup procedures in place
- Easy troubleshooting

**Overall Risk Level:** **LOW** - Safe for production deployment

---

## Deployment Process

### Development Deployment (Local Testing)

```bash
# Activate venv
source venv/bin/activate

# Run monitor locally
cd dashboard
python monitor.py

# Test in browser
firefox http://localhost:8000
```

### Production Deployment (Automated)

**Option 1: Full Automated Deployment (Recommended)**

```bash
# Run on any machine with network access to all servers
git clone https://github.com/JBakers/pihole-sentinel.git
cd pihole-sentinel
sudo python3 setup.py

# Choose option 2: "Deploy complete setup via SSH"
# Script will:
# - Generate SSH keys
# - Distribute keys to all servers
# - Install dependencies
# - Deploy monitor and keepalived
# - Start services
# - Cleanup sensitive files
```

**Option 2: Manual Deployment**

1. Generate configs:
   ```bash
   sudo python3 setup.py
   # Choose option 1: "Generate configuration files only"
   ```

2. Copy to each server manually:
   ```bash
   # Primary Pi-hole
   scp generated_configs/primary_keepalived.conf root@primary:/etc/keepalived/keepalived.conf
   scp generated_configs/primary.env root@primary:/etc/keepalived/.env

   # Secondary Pi-hole
   scp generated_configs/secondary_keepalived.conf root@secondary:/etc/keepalived/keepalived.conf
   scp generated_configs/secondary.env root@secondary:/etc/keepalived/.env

   # Monitor
   scp generated_configs/monitor.env root@monitor:/opt/pihole-monitor/.env
   ```

3. Install and start services on each host

4. **IMPORTANT:** Delete `generated_configs/` directory
   ```bash
   rm -rf generated_configs/
   ```

### Upgrading Existing Installation

```bash
# On monitor server
sudo systemctl stop pihole-monitor
cd /opt/pihole-monitor
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl start pihole-monitor

# On Pi-hole servers
sudo systemctl restart keepalived
```

### Rollback Procedure

Setup script automatically creates backups:

```bash
# Backups stored with timestamp
ls /etc/keepalived/*.backup_*
ls /opt/pihole-monitor/*.backup_*

# Restore from backup
sudo cp /etc/keepalived/keepalived.conf.backup_20251114_123456 /etc/keepalived/keepalived.conf
sudo systemctl restart keepalived
```

---

## Common Pitfalls

### 1. Python 3.13+ Externally Managed Environment

**Problem:**
```
error: externally-managed-environment
× This environment is externally managed
```

**Solution:**
- **NEVER** use `pip install --break-system-packages`
- **ALWAYS** create a virtual environment:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```

### 2. CRLF Line Endings in Bash Scripts

**Problem:**
```
bash: ./script.sh: /bin/bash^M: bad interpreter
```

**Solution:**
- Ensure all `.sh` files use LF line endings (not CRLF)
- Setup script auto-converts: `sed -i 's/\r$//' script.sh`
- Configure git: `git config --global core.autocrlf input`

### 3. Missing Environment Variables

**Problem:**
```
Missing required environment variables: PRIMARY_PASSWORD, SECONDARY_PASSWORD
```

**Solution:**
- Create `.env` file in dashboard directory
- Copy from `.env.example` and fill in values
- Verify with: `grep -v '^#' .env | grep '='`

### 4. SSH Key Authentication Failures

**Problem:**
```
Permission denied (publickey)
```

**Solution:**
- Run `setup.py` which generates and distributes keys automatically
- Manually verify: `ssh -i ~/.ssh/id_pihole_sentinel root@pihole1 echo OK`
- Check key permissions: `chmod 600 ~/.ssh/id_pihole_sentinel`

### 5. VIP Detection Failures

**Problem:**
```
Warning: Could not determine VIP location - No MAC address found
```

**Solution:**
- Ensure monitor can reach VIP: `ping <VIP>`
- Check ARP table: `ip neigh show`
- Verify network interface is correct in keepalived config
- VIP detection retries 3 times automatically (added in v0.8.0)

### 6. DHCP Misconfiguration Warnings

**Problem:**
Dashboard shows "DHCP Misconfigured"

**Root Causes:**
- MASTER node has DHCP disabled (should be enabled)
- BACKUP node has DHCP enabled (should be disabled)

**Solution:**
- Check keepalived state: `systemctl status keepalived`
- Check DHCP status via Pi-hole admin panel
- Verify `dhcp_control.sh` is working: `/usr/local/bin/dhcp_control.sh enable`

### 7. Hardcoded Network Interface

**Problem:**
```
arping: Device eth0 not available
```

**Solution:**
- Ensure `INTERFACE` variable is set in keepalived environment
- Check `/etc/keepalived/.env` has correct interface (e.g., `ens18`)
- Verify with: `ip link show`

### 8. Database Permission Issues

**Problem:**
```
PermissionError: [Errno 13] Permission denied: '/opt/pihole-monitor/monitor.db'
```

**Solution:**
- Check ownership: `ls -l /opt/pihole-monitor/`
- Fix ownership: `sudo chown -R pihole-monitor:pihole-monitor /opt/pihole-monitor/`
- Verify service user: `systemctl status pihole-monitor`

### 9. Remote Dashboard Access / CORS Issues

**Problem:**
Dashboard works on localhost but fails when accessing remotely
```
Access to fetch at 'http://<monitor-ip>:8080/api/status' from origin 'http://<your-ip>' has been blocked by CORS policy
```

**Solution:**
- Edit `dashboard/monitor.py` CORS configuration (lines 154-167)
- Add your access IP to `allow_origins` list:
  ```python
  allow_origins=[
      "http://localhost:8080",
      "http://127.0.0.1:8080",
      "http://<monitor-ip>:8080",  # Add this line
  ],
  ```
- Restart monitor service: `sudo systemctl restart pihole-monitor`
- **Security Note:** For production, consider:
  - Setting up reverse proxy (nginx/traefik) with HTTPS
  - Using domain names instead of IP addresses
  - Implementing proper firewall rules

**Audit Finding:**
- Priority: 🔴 HIGH
- Impact: Enables remote dashboard access
- See: AUDIT_REPORT_20251116.md section 1.5

---

## Security Considerations

### Sensitive Data Handling

1. **Pi-hole Passwords**
   - Stored in `.env` files with `chmod 600`
   - Never committed to git (in `.gitignore`)
   - Required for API authentication only

2. **Keepalived Passwords**
   - Generated with `secrets.choice()` (32 chars)
   - Stored in keepalived.conf (auth_pass)
   - Used for VRRP authentication

3. **SSH Keys**
   - Ed25519 keys generated automatically
   - Stored in `~/.ssh/id_pihole_sentinel`
   - Public key distributed to all servers
   - Passwords only used once during setup, then cleared from memory

4. **Generated Configs Cleanup**
   - `setup.py` generates configs in `generated_configs/`
   - Contains passwords and secrets in plaintext
   - Automatically overwritten with random data after deployment
   - Directory completely removed
   - Cleanup happens on success, error, or Ctrl+C

### File Permissions

- **`.env` files:** `600` (root:root) - Contains passwords
- **`keepalived.conf`:** `644` (root:root) - Contains auth_pass
- **Scripts:** `755` (root:root) - Executable by root
- **Database:** `644` (pihole-monitor:pihole-monitor) - Writable by service
- **Monitor files:** `644` (pihole-monitor:pihole-monitor) - Readable by service

### Network Security

- Monitor polls Pi-holes over HTTP (consider HTTPS in future)
- VRRP uses password authentication (consider using AH in future)
- SSH key-based authentication (passwords only for initial setup)
- All servers should be on trusted network (isolated VLAN recommended)

### Best Practices

1. **Strong Pi-hole passwords** - 16+ characters, mixed case, numbers, symbols
2. **Firewall rules** - Restrict access to monitor dashboard (port 8080)
3. **Regular updates** - `apt update && apt upgrade` weekly
4. **Log monitoring** - Review `/var/log/keepalived-notify.log` weekly
5. **Backup configs** - Setup script creates timestamped backups automatically
6. **SSH hardening** - Disable password auth after key distribution

---

## Contributing Changes

### Before Submitting Changes

1. **Test thoroughly** in development environment
2. **Update CHANGELOG.md** with changes
3. **Update VERSION** if needed (semantic versioning)
4. **Update documentation** (README.md, DEVELOPMENT.md, or this file)
5. **Check code style** (logging, async patterns, error handling)
6. **Verify no hardcoded values** (use environment variables)

### Commit Message Format

```
type: brief description (50 chars max)

Longer explanation if needed (72 chars per line).
Explain what and why, not how.

Fixes #123
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples:**
- `feat: add support for custom notification endpoints`
- `fix: retry VIP detection on ARP table population failure`
- `docs: update CLAUDE.md with new deployment process`
- `chore: bump dependency versions for security patches`

### Pull Request Checklist

- [ ] Changes tested in staging environment
- [ ] CHANGELOG.md updated
- [ ] Documentation updated
- [ ] No sensitive data in commits
- [ ] Code follows existing conventions
- [ ] Backward compatible (or migration path documented)

---

## Quick Reference

### Common Commands

```bash
# Development
source venv/bin/activate             # Activate venv
python dashboard/monitor.py          # Run monitor locally
deactivate                           # Exit venv

# Production
systemctl status pihole-monitor      # Check monitor status
systemctl status keepalived          # Check keepalived status
journalctl -u pihole-monitor -f      # Monitor logs (live)
tail -f /var/log/keepalived-notify.log  # Keepalived events

# Debugging
ip addr show                         # Show all IPs (including VIP)
ip neigh show                        # Show ARP table
dig @<VIP> example.com               # Test DNS via VIP
sqlite3 /opt/pihole-monitor/monitor.db "SELECT * FROM status_history ORDER BY timestamp DESC LIMIT 5;"

# Failover Testing
systemctl stop pihole-FTL            # Trigger failover
systemctl start pihole-FTL           # Restore service

# Configuration
cat /etc/keepalived/keepalived.conf  # View keepalived config
cat /opt/pihole-monitor/.env         # View monitor config (sensitive!)
```

### File Locations Reference

| Component | Config | Logs | Service |
|-----------|--------|------|---------|
| Monitor | `/opt/pihole-monitor/.env` | `/var/log/pihole-monitor.log` | `pihole-monitor.service` |
| Keepalived | `/etc/keepalived/keepalived.conf` | `/var/log/keepalived-notify.log` | `keepalived.service` |
| Sync | `/usr/local/bin/sync-pihole-config.sh` | stdout/stderr | `pihole-sync.timer` |
| Notifications | `/opt/pihole-monitor/notify_settings.json` | In keepalived log | Part of keepalived |

---

## Version History

- **v0.9.0-beta.2** (2025-11-16) - Quality Assurance Update
  - ✅ **Comprehensive code audit completed** (Score: 89/100 - Excellent)
    - Security audit: 95/100 (Excellent)
    - Code quality: 90/100 (Excellent)
    - Documentation: 95/100 (Outstanding)
    - Overall: Production Ready
  - 📝 **Added test automation infrastructure**
    - Standardized test documentation template (802 lines)
    - Test automation guide with scripts (700 lines)
    - Automated test scripts (syntax, quality, security, failover, dashboard)
    - CI/CD integration examples
  - 📊 **Enhanced documentation**
    - Added comprehensive audit report (AUDIT_REPORT_20251116.md - 1,300+ lines)
    - Updated CLAUDE.md with audit results and test infrastructure
    - Added Code Quality & Audit section to CLAUDE.md
    - Reorganized Additional Resources with categorization
  - 🔧 **Quality improvements based on audit**
    - Documented all security practices and file permissions
    - Added code quality standards and automated checks
    - Created risk assessment framework
    - Defined priority roadmap for improvements

- **v0.9.0-beta.1** (2025-11-14)
  - Automatic API key injection during deployment
  - Enhanced notification reliability with retry logic
  - Improved VIP detection with ARP table population delay
  - Added comprehensive testing guide (TESTING-GUIDE.md)
  - Updated dependencies to latest secure versions
  - Replaced print() with proper logging in monitor.py
  - Fixed hardcoded network interface in scripts
  - Auto-detect timezone in setup.py
  - Improved error handling in sync script

- **Previous versions** - See CHANGELOG.md

---

## Additional Resources

### User Documentation

- **README.md** - User-facing documentation and installation guide
- **QUICKSTART.md** - Quick start guide for rapid deployment
- **EXISTING-SETUP.md** - Guide for adding HA to existing Pi-hole installations
- **SYNC-SETUP.md** - Configuration synchronization guide
- **TESTING-GUIDE.md** - User testing guide for production deployments

### Developer Documentation

- **DEVELOPMENT.md** - Development environment setup for contributors
- **CLAUDE.md** - This file - AI assistant guide for codebase
- **CHANGELOG.md** - Detailed version history and change log
- **BRANCHING_STRATEGY.md** - Git workflow and branching strategy

### Quality Assurance Documentation

- **AUDIT_REPORT_20251116.md** - Comprehensive code audit report (1,300+ lines)
  - Security audit (95/100)
  - Code quality audit (90/100)
  - Testing assessment (60/100)
  - Documentation audit (95/100)
  - Priority recommendations and roadmap

- **`.github/TESTING_TODO.md`** - Complete testing checklist for `testing` branch (296 items)
  - Pre-merge checklist
  - Integration tests
  - Performance tests
  - Security tests
  - Browser compatibility
  - Sign-off criteria

- **`.github/TEST_DOCUMENTATION_TEMPLATE.md`** - Standardized test report template (802 lines)
  - Test execution report format
  - Performance metrics tracking
  - Bug tracking tables
  - Sign-off criteria

- **`.github/TEST_AUTOMATION_GUIDE.md`** - Test automation guide (700 lines)
  - Automated test scripts (syntax, quality, security)
  - Failover and dashboard test automation
  - CI/CD integration examples
  - Nightly and weekly test schedules

### Project Management

- **`.github/BRANCH_PROTECTION.md`** - Branch protection setup guide
- **`.github/CODEOWNERS`** - Code ownership and review assignments
- **`.github/DEVELOP_TODO.md`** - Development branch todo list
- **`.github/workflows/code-quality.yml`** - Automated CI/CD quality checks

### Issue Templates

- **`.github/ISSUE_TEMPLATE/bug_report.md`** - Bug report template
- **`.github/ISSUE_TEMPLATE/feature_request.md`** - Feature request template
- **`.github/PULL_REQUEST_TEMPLATE.md`** - Pull request template

---

**Last Updated:** 2025-11-16
**Maintainer:** JBakers
**Repository:** https://github.com/JBakers/pihole-sentinel

For questions or issues, please open a GitHub issue.
