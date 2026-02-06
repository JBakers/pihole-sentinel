# Pi-hole Sentinel - AI Agent Instructions

## 🚨 FUNDAMENTELE REGELS (NOOIT OVERTREDEN)

### 1. COMMIT APPROVAL - ALTIJD TOESTEMMING VRAGEN
**CRITICAL RULE:** Vraag ALTIJD toestemming voor ELKE commit. NOOIT automatisch committen.

**Workflow:**
1. ✅ Maak wijzigingen in files
2. ✅ Test de wijzigingen
3. ✅ Stage files met `git add`
4. ❌ **STOP HIER** - Commit NIET automatisch
5. ✅ Vraag gebruiker: "Zal ik deze changes committen?"
6. ✅ Wacht op expliciete toestemming (ja/yes/commit)
7. ✅ Pas dan: `git commit -m "message"` en `git push`

**Verboden:**
- ❌ Auto-commit na elke wijziging
- ❌ Batch commits zonder toestemming
- ❌ Git hooks die automatisch committen
- ❌ Committen "omdat het klaar is"

**Toegestaan:**
- ✅ `git status` checken
- ✅ `git diff` tonen
- ✅ Files stagen met `git add`
- ✅ Commit message voorbereiden

### 2. BRANCH RESTRICTIONS - NOOIT MERGEN NAAR PROTECTED BRANCHES
**CRITICAL RULE:** AI agents mogen ALLEEN committen naar de `develop` branch.

**Verplicht:**
- ✅ AI agents mogen **ALLEEN** committen naar `develop` branch
- 🚫 AI agents mogen **NOOIT** mergen naar `testing` branch
- 🚫 AI agents mogen **NOOIT** mergen naar `main` branch
- 🚫 AI agents mogen **NOOIT** pushen naar `testing` of `main`
- ✅ **Alleen de repository owner** mag mergen: `develop` → `testing` → `main`

**Git Hook Protectie:**
- Pre-merge-commit hook in `.githooks/pre-merge-commit` blokkeert protected branch merges
- Installeer hooks: `git config core.hooksPath .githooks`

**Bij Per Ongeluk Merge:**
```bash
git merge --abort          # Abort de merge
git checkout develop       # Terug naar develop
```

### 3. VERSION BUMP - ALTIJD BIJ CODE CHANGES
**CRITICAL RULE:** Elke commit met code changes MOET version bump bevatten.

**Verplicht bij elke commit:**
1. ✅ Update `VERSION` file met nieuwe versie
2. ✅ Update `CHANGELOG.md` met gedetailleerde entry
3. ✅ Update `CLAUDE.md` header (lines 3-4) met nieuwe versie en datum

**Semantic Versioning (Beta Phase):**
- Format: `MAJOR.MINOR.PATCH-beta.INCREMENT` (bijv. `0.12.0-beta.7`)
- 🔴 Breaking change? → Bump MINOR, reset naar beta.1
- 🟡 New feature? → Increment beta number
- 🟢 Bug fix? → Increment beta number
- ⚪ Documentation only? → Geen version change nodig

### 4. TESTING - ALTIJD LOKAAL TESTEN
**CRITICAL RULE:** Test code changes ALTIJD voordat je commit.

**Test Commands:**
```bash
# Activeer virtual environment
source venv/bin/activate

# Run pytest tests
make test

# Of specifieke tests
pytest tests/ -v

# Syntax check
python3 -m py_compile dashboard/monitor.py setup.py
bash -n keepalived/scripts/*.sh
```

## 📚 Terminologie (Teach User Correct Terms)

Bij elke interactie, gebruik de correcte terminologie:

### Git & Version Control
| Term | Betekenis |
|------|-----------|
| **Repository (repo)** | Git database met alle versies van de code |
| **Working tree** | Lokale kopie van bestanden op disk |
| **Staging area / Index** | Bestanden klaar voor commit (`git add`) |
| **Commit** | Snapshot van staged changes met message |
| **Push** | Lokale commits uploaden naar remote (GitHub) |
| **Pull** | Remote changes downloaden naar lokaal |
| **Branch** | Parallelle versie van de code |
| **Merge** | Branches samenvoegen |

### Testing
| Term | Betekenis |
|------|-----------|
| **Unit test** | Test van één functie/component |
| **Integration test** | Test van meerdere componenten samen |
| **Test suite** | Verzameling van alle tests |
| **Test coverage** | Percentage code gedekt door tests |

## Project Overview

**Pi-hole Sentinel** - High Availability for Pi-hole DNS servers.

**Features:**
- 🔄 Automatic failover via Virtual IP (VIP) using VRRP/Keepalived
- 📊 Real-time web dashboard (FastAPI + SQLite)
- 🔔 Smart notifications (Telegram, Discord, Pushover, Ntfy, webhooks)
- 🔧 Automated deployment via `setup.py`

**Target:** Linux systems (Debian/Ubuntu) with Pi-hole v6.0+

### 📋 Critical Documents
- **CLAUDE.md** - Complete AI assistant guide (1943 lines)
- **CHANGELOG.md** - Version history and release notes
- **VERSION** - Current version (single source of truth)
- **TODO_USER.md** - User-managed task tracking

## Architecture

### Directory Structure
```
pihole-sentinel/
├── dashboard/                 # Monitor service (FastAPI)
│   ├── monitor.py            # Main monitoring service
│   ├── index.html            # Dashboard UI
│   ├── settings.html         # Notification settings UI
│   └── .env.example          # Environment template
├── keepalived/               # VRRP failover config
│   ├── pihole1/              # Primary node config
│   ├── pihole2/              # Secondary node config
│   └── scripts/              # Health check & notification scripts
├── systemd/                  # Systemd service files
├── tests/                    # Pytest test suite
├── docs/                     # Documentation
├── setup.py                  # Automated deployment script
├── sync-pihole-config.sh     # Configuration sync script
├── requirements.txt          # Python dependencies
└── Makefile                  # Development commands
```

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│  ┌──────────────┐         VIP          ┌──────────────┐    │
│  │  Primary     │◄─────(Keepalived)────►│  Secondary   │    │
│  │  Pi-hole     │      VRRP Protocol    │  Pi-hole     │    │
│  └──────┬───────┘                       └───────┬──────┘    │
│         │            ┌──────────────┐           │           │
│         └────────────►   Monitor    ◄───────────┘           │
│                      │   (FastAPI)  │                       │
│                      └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Python 3.8+** (tested with 3.13)
  - FastAPI - Web framework
  - Uvicorn - ASGI server
  - aiohttp - Async HTTP client
  - aiosqlite - Async SQLite
  - pytest - Testing framework
- **Bash** - Health checks, notifications, sync scripts
- **SQLite** - Status history and event storage
- **Keepalived** - VRRP implementation for failover

## Critical Patterns

### Communication & Language
- **Communicatie:** altijd in het Nederlands met de gebruiker
- **Code & strings:** altijd in het Engels (code, comments, user-facing tekst)

### Python Code Style

1. **Logging over Print**
   ```python
   # ✅ CORRECT
   logger.info("API call successful")
   logger.error(f"API call failed: {e}", exc_info=True)
   
   # ❌ WRONG
   print("API call successful")
   ```

2. **Async/Await Pattern**
   ```python
   async def check_pihole(ip: str) -> Dict[str, bool]:
       async with aiohttp.ClientSession() as session:
           async with session.get(f"http://{ip}/api") as response:
               return await response.json()
   ```

3. **Error Handling**
   ```python
   try:
       result = await api_call()
   except Exception as e:
       logger.error(f"API call failed: {e}", exc_info=True)
       # Graceful degradation
   ```

### Bash Script Style

1. **Shebang & Error Handling**
   ```bash
   #!/bin/bash
   set -e  # Exit on error
   ```

2. **Logging with Timestamp**
   ```bash
   timestamp() { date "+%Y-%m-%d %H:%M:%S"; }
   echo "$(timestamp) - Action performed" >> "$LOGFILE"
   ```

3. **Line Endings**
   - ALTIJD LF (Unix), NOOIT CRLF (Windows)
   - Auto-convert: `sed -i 's/\r$//' script.sh`

### File Permissions
- **Config files with secrets:** `600` (root:root)
- **Application files:** `644` (service_user:service_user)
- **Executable scripts:** `755` (root:root)

## Development Workflow

### Version Management
**Centralized Version System:**
- **Single Source of Truth:** `VERSION` file (e.g., `0.12.0-beta.7`)
- **CHANGELOG.md:** Detailed change log per version
- **CLAUDE.md header:** Must be updated with version

**Pre-Commit Verification Checklist:**
- [ ] `VERSION` file updated
- [ ] `CHANGELOG.md` has new entry
- [ ] `CLAUDE.md` header updated (line 4)
- [ ] No `print()` statements in Python code (use `logger.*()`)
- [ ] All bash scripts use LF line endings

### Branch Strategy
**Three-tier structure:**

1. **`develop` branch** - Active development:
   - Waar AI agents werken
   - Alle development happens hier
   - De enige branch waar AI mag committen

2. **`testing` branch** - Quality assurance:
   - Manual testing en QA
   - Alleen user mag mergen van develop → testing

3. **`main` branch** - Production:
   - Stable releases alleen
   - Alleen user mag mergen van testing → main

**Workflow Rules:**
- ✅ All AI development on `develop` branch
- ✅ Test with `make test` before commits
- ❌ Never merge to `testing` or `main` (only user may)

### Commit Message Format
```
type: brief description (50 chars max)

Longer explanation if needed.
What changed and why.

Version: X.Y.Z-beta.N
```

**Valid types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `security`

### Testing

**Run Tests:**
```bash
# Full test suite with coverage
make test

# Quick tests without coverage
make test-fast

# Specific test file
pytest tests/test_validation.py -v

# Code quality
make lint
make format
```

**Test Structure:**
- `tests/test_validation.py` - Input validation tests
- `tests/test_vip_detection.py` - VIP detection tests
- `tests/test_api_handlers.py` - API endpoint tests
- `tests/test_dhcp_parsing.py` - DHCP config parsing tests
- `tests/test_error_handling.py` - Error handling tests

### Development Setup

```bash
# Clone repository
git clone https://github.com/JBakers/pihole-sentinel.git
cd pihole-sentinel

# Create virtual environment (REQUIRED for Python 3.13+)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install git hooks
git config core.hooksPath .githooks

# Run monitor locally
cd dashboard
python monitor.py
# Access at http://localhost:8000
```

## Common Tasks

### Making Changes to Monitor Service

1. Activate venv: `source venv/bin/activate`
2. Edit `dashboard/monitor.py`
3. Test locally: `cd dashboard && python monitor.py`
4. Run tests: `make test`
5. Commit (with user approval)

### Making Changes to Keepalived Scripts

1. Edit script in `keepalived/scripts/`
2. Syntax check: `bash -n keepalived/scripts/script.sh`
3. Test on staging environment (not production!)
4. Commit (with user approval)

### Adding New Features

1. Update `CHANGELOG.md` with entry
2. Update `VERSION` file
3. Update `CLAUDE.md` header
4. Test thoroughly
5. Commit (with user approval)

## Configuration

**Environment Variables (dashboard/.env):**
```env
PRIMARY_IP=10.10.100.10
PRIMARY_NAME="Primary Pi-hole"
PRIMARY_PASSWORD=your_pihole_password

SECONDARY_IP=10.10.100.20
SECONDARY_NAME="Secondary Pi-hole"
SECONDARY_PASSWORD=your_pihole_password

VIP_ADDRESS=10.10.100.2
CHECK_INTERVAL=10
```

## Security Notes

- All Python code uses `logger.*()` instead of `print()`
- Input validation prevents SQL injection (parameterized queries)
- Passwords stored in `.env` files with `chmod 600`
- SSH keys via Ed25519 (automated setup)
- Sensitive files securely deleted after deployment

**Never commit:**
- `.env` files (in `.gitignore`)
- Pi-hole passwords
- SSH private keys

## Code Quality Standards

**Audit Score:** 89/100 (Excellent)

| Category | Score |
|----------|-------|
| Security | 95/100 |
| Code Quality | 90/100 |
| Documentation | 95/100 |
| Architecture | 95/100 |

**Quality Checks:**
```bash
make lint              # Run pylint, flake8
make format            # Format with black, isort
make check-security    # Run bandit, safety
```

## Critical Rules

### 🚨 NEVER DO THIS
1. **NEVER merge to testing/main** - Only user merges via merge flow
2. **Delete files without permission** - `VERSION`, `CLAUDE.md`, `CHANGELOG.md` are critical
3. **Commits without user approval** - Always ask before committing
4. **Skip version bumps** - Every code commit needs VERSION + CHANGELOG update
5. **Use print() in monitor.py** - Always use `logger.*()` instead
6. **Commit broken code** - Test with `make test` before committing
7. **CRLF line endings** - Always use LF for bash scripts

### TODO_USER.md Structure
User-managed task tracking file. AI should:
- ✅ Read en reference tasks
- ❌ Never delete completed tasks without permission
- ✅ Suggest updates, maar user bepaalt

## Quick Reference

### Common Commands

```bash
# Development
source venv/bin/activate             # Activate venv
python dashboard/monitor.py          # Run monitor locally
make test                            # Run all tests
make lint                            # Code quality check

# Git (only on develop branch!)
git checkout develop                 # Switch to develop
git add .                            # Stage changes
git status                           # Check status
# STOP - Ask user before commit!

# Debugging
python3 -m py_compile file.py        # Syntax check Python
bash -n script.sh                    # Syntax check Bash
```

### File Locations Reference

| Component | Location | Purpose |
|-----------|----------|---------|
| Monitor | `dashboard/monitor.py` | FastAPI monitoring service |
| Tests | `tests/` | Pytest test suite |
| Keepalived | `keepalived/scripts/` | Health check scripts |
| Config | `dashboard/.env` | Environment variables |
| Version | `VERSION` | Current version |
| Changelog | `CHANGELOG.md` | Version history |
| AI Guide | `CLAUDE.md` | Complete AI assistant guide |

---

**Last Updated:** 2026-02-06
**Maintainer:** JBakers
**Repository:** https://github.com/JBakers/pihole-sentinel

Voor complete details, zie [CLAUDE.md](../CLAUDE.md) (1943 lines).
