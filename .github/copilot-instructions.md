# Pi-hole Sentinel - AI Agent Instructions (GitHub Copilot)

**📖 LEES ALTIJD CLAUDE.MD VOOR VOLLEDIGE INSTRUCTIES**

Dit is een kort referentiebestand voor GitHub Copilot.
**Alle uitgebreide instructies staan in [CLAUDE.md](../CLAUDE.md) (1943 lines).**

---

## 🚨 4 FUNDAMENTELE REGELS (NOOIT OVERTREDEN)

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

---

**Zie [CLAUDE.md](../CLAUDE.md) voor:**
- Volledige regels met voorbeelden (400+ regels)
- Architectuur & codebase structuur
- Common pitfalls & oplossingen
- Deployment process
- Security considerations
- Testing guidelines
- En veel meer...

---

## 📚 Quick Terminologie (volledige tabel in CLAUDE.md)

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

---

## 🗣️ Communicatie & Taal

- **Met gebruiker:** Altijd Nederlands
- **Code & strings:** Altijd Engels
- **Zie CLAUDE.md voor volledige uitleg**

---

## Quick Project Overview

**Pi-hole Sentinel** - High Availability for Pi-hole DNS servers.

**Key Features:**
- 🔄 Automatic failover via VIP (VRRP/Keepalived)
- 📊 Real-time web dashboard (FastAPI + SQLite)
- 🔔 Smart notifications (Telegram, Discord, Pushover, Ntfy)
- 🔧 Automated deployment via `setup.py`

**Target:** Linux systems (Debian/Ubuntu) with Pi-hole v6.0+

**Critical Documents:**
- **CLAUDE.md** - Complete AI assistant guide (1943 lines) ← **LEES DIT**
- **CHANGELOG.md** - Version history
- **VERSION** - Current version (single source of truth)
- **TODO_USER.md** - User-managed task tracking

---

## 🛠️ Quick Development Commands

```bash
# Development
source venv/bin/activate             # Activate venv
python dashboard/monitor.py          # Run monitor locally
make test                            # Run all tests
make lint                            # Code quality check

# Docker Testing
make docker-up                       # Start test environment (17 containers)
make docker-down                     # Stop containers
make docker-status                   # Status overview
make docker-test                     # Smoke tests

# Git (only on develop branch!)
git checkout develop                 # Switch to develop
git add .                            # Stage changes
git status                           # Check status
# ❌ STOP - Ask user before commit!

# Debugging
python3 -m py_compile file.py        # Syntax check Python
bash -n script.sh                    # Syntax check Bash
```

---

**Last Updated:** 2026-02-06  
**Maintainer:** JBakers  
**Repository:** https://github.com/JBakers/pihole-sentinel

**📖 Voor complete details, zie altijd [CLAUDE.md](../CLAUDE.md) (1943 lines).**
