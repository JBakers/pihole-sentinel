# Changelog

All notable changes to Pi-hole Sentinel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.12.0-beta.1] - 2025-12-07

### ✨ New Features

#### Debian 12/13 Compatibility
- Dynamic Python package resolution (`python3-dev` → `python3.13-dev` on Debian 13)
- `apt-cache show` check before installation to find available packages
- Automatic fallback to generic package names

#### Uninstaller
- New CLI: `sudo python3 setup.py --uninstall`
- Options: `--keep-configs` (preserve config files), `--dry-run` (preview mode)
- Interactive wizard with local and remote uninstall options
- Troubleshooting tips for failed remote uninstalls

#### Update Notifications
- New `/api/check-update` endpoint checks GitHub releases
- Dashboard shows banner when new version is available
- Cached checks (every 6 hours) to respect GitHub API limits
- Dismiss button remembers version (won't show again for same version)

### 🔧 Improved

- Better package resolution error messages
- Progress indicators during package resolution

---

## [0.11.0-beta.4] - 2025-12-07

### 🔒 Security Fixes

#### Password Generation (CRITICAL)
- **Fixed**: Removed special characters from generated passwords that broke keepalived config
- Now uses only alphanumeric characters (a-z, A-Z, 0-9)
- Prevents shell parsing issues in config files

#### Shell Injection Prevention
- **Fixed**: `escape_for_bash_config()` added to monitor.py for safe credential writing
- **Fixed**: Timezone validation in setup.py to prevent command injection
- **Fixed**: `.env` file value escaping in setup.py
- **Fixed**: JSON escaping in notify.sh for Discord/webhook payloads
- **Fixed**: Quoted shell variables in keepalived_notify.sh

### 🔧 Improved

- Added `escape_json()` function to notify.sh for safe JSON construction
- Added `validate_timezone()` method to setup.py
- Added `escape_for_env_file()` method to setup.py
- Better variable quoting in keepalived_notify.sh (arping command)

### 📝 Audit

Completed comprehensive security audit covering:
- Password/secret generation
- Config file writing
- Shell command construction
- Template variable substitution

---

## [0.11.0-beta.3] - 2025-12-07

### 🎨 Improved

#### Settings Page UI Overhaul
- **Softer background colors**: Changed from bright white to subtle light gray (rgba 241,245,249)
- **Compact notification cards**: Reduced padding and margins for cleaner look
- **Descriptive text**: Each notifier now has helpful description text
  - Telegram: "Receive instant alerts via Telegram bot"
  - Discord: "Post alerts to a Discord channel via webhook"
  - Pushover: "Push notifications to iOS/Android devices"
  - Ntfy: "Open source push notifications (self-hosted or public)"
  - Webhook: "Send JSON payloads to any endpoint"
- **Dark mode improvements**: Better contrast with darker card backgrounds
- **Version display fix**: Now properly fetches version from API with fallback

### 🔧 Fixed

- Version badge in README.md now shows correct version (v0.11.0-beta.2)
- QUICKSTART.md now references correct branch (testing)
- Added API_KEY example to .env.example
- loadVersion() now uses API_BASE and includes API key header

---

## [0.11.0-beta.2] - 2025-12-07

### ✨ New

#### Repeat/Reminder Notifications (Fase 2)
- **Repeat alerts**: Send reminder notifications while issues persist
- Configurable intervals: Off / 5 min / 10 min / 30 min / 60 min
- Automatic tracking of active issues (failover, fault)
- Reminders include "🔔 REMINDER:" prefix

#### Snooze Notifications (Fase 3)
- **Snooze functionality**: Temporarily disable notifications (for maintenance)
- Quick snooze buttons: 1 hour / 4 hours / 24 hours
- Visual snooze status display with cancel button
- New API endpoints:
  - `GET /api/notifications/snooze` - Get snooze status
  - `POST /api/notifications/snooze` - Set snooze (duration in minutes)
  - `DELETE /api/notifications/snooze` - Cancel snooze

### 🎨 Improved

- Settings UI now includes Repeat Alerts section
- Settings UI now includes Snooze section with status display
- Better notification state tracking in monitor loop

---

## [0.11.0-beta.1] - 2025-12-07

### ✨ New

#### Custom Message Templates UI
- **Templates Modal**: New popup modal for editing all 4 notification templates
- **Template types**: Failover, Recovery, Fault, and Startup
- **Clickable variables**: `{master}`, `{backup}`, `{primary}`, `{secondary}`, `{reason}`, `{time}`, `{date}`, `{vip}`
- **Clickable emoji buttons**: ⚔️ 🚨 🆘 ✅ ⚠️ 🔴 🟢 with visual styling
- **Per-template test buttons**: Test each template individually with sample data
- **Reset to defaults**: Restore all templates to original values
- **New API endpoint**: `/api/notifications/test-template` for template testing

### 🎨 Improved

#### UI/UX Enhancements
- **Sticky header and variables bar**: Always visible when scrolling in templates modal
- **Dark mode toggle button**: Floating button in bottom-right corner
- **Dark mode fixes**: All modal labels and text now readable in dark mode
- **Escape key support**: Close templates modal with Escape key
- **Larger modal**: 90vh max height for better template editing

#### Template Variables
- Added `{master}` - current MASTER node name
- Added `{backup}` - current BACKUP node name  
- Added `{primary}` - Primary Pi-hole name
- Added `{secondary}` - Secondary Pi-hole name
- Added `{time}` and `{date}` - timestamp of event
- Improved default templates with clearer messaging

### 🔧 Fixed

- Type hint fix: `http_session: aiohttp.ClientSession | None = None`

---

## [0.10.0-beta.20] - 2025-12-07

### ✨ Improved

#### Setup Quick IP Flow
- Added auto-detection of local IP range for quick setup; falls back to manual range entry if detection fails.
- Quick setup now remembers the chosen range and reuses it for subsequent prompts.
- Monitor server IP prompt reuses the detected/selected range and only asks for the last octet (no auto .50 default).
- Validation and prompts now use colored output and explicit error messages.

#### Banner & Version Display
- Setup banner now reads version from `VERSION` via `_get_version_banner()`.
- Updated ASCII banner to match logo style.

---

## [0.10.0-beta.19] - 2025-12-06

### ✨ New

#### Advanced Notification Features - Phase 1
- **Custom message templates:**
  - Templates support variable substitution: `{node_name}`, `{reason}`, `{vip_address}`
  - Default templates for: failover, recovery, fault events
  - Editable via settings interface (planned in UI update)
  - Example: `"🛡️ Pi-hole Sentinel Alert\n\n<b>{node_name} became MASTER</b>\n\nReason: {reason}\nVIP: {vip_address}"`
- **Event logging for notifications:**
  - Logs when notifications are sent: `✉️ Notification sent: failover (1 service)`
  - Logs failed notifications: `⚠️ Notification failed for: Telegram (HTTP 500)`
  - Visible in System Events timeline
- **Multi-service notification support:**
  - Telegram (with HTML formatting)
  - Discord (with markdown conversion)
  - Pushover (plain text)
  - Ntfy (plain text)
  - Custom webhooks (JSON with full context)
  - All services can be enabled simultaneously
  - Tracks success/failure per service

### 🐛 Fixed

#### VIP Address Configuration
- **Fixed incorrect config key:**
  - Changed `CONFIG['vip_address']` → `CONFIG['vip']` in failover notification code
  - Prevents KeyError when sending failover notifications
  - Aligns with actual CONFIG structure (line 66)

### 📝 Technical Details

#### Code Changes
- **`dashboard/monitor.py` (lines 154-327):**
  - Completely rewritten `send_notification()` function
  - Changed signature: `(event_type: str, message: str)` → `(event_type: str, template_vars: dict)`
  - Loads templates from JSON settings file
  - Supports all notification services (not just Telegram)
  - Logs success/failure to events database
  - Format conversion for Discord (HTML → Markdown) and Pushover/Ntfy (HTML tags removed)
- **`dashboard/monitor.py` (lines 738-744):**
  - Updated failover detection to pass template variables
  - Sends `{node_name, reason, vip_address}` dict to notification function

### 🔮 Coming Next

- **Phase 2:** Repeat/reminder logic (5/10/30/60 min intervals)
- **Phase 3:** Snooze functionality
- Settings UI update to edit message templates

---

## [0.10.0-beta.18] - 2025-12-06

### ✨ Improved

#### Notification Architecture
- **Centralized notifications on monitor service:**
  - **Change:** Notifications now handled entirely by monitor service instead of by keepalived on Pi-holes
  - **Benefit:** Simpler architecture, no configuration sync needed between servers
  - Monitor detects failover events and sends notifications (Telegram, Discord, Pushover, etc.)
  - `notify.conf` only needs to exist on monitor server (not on Pi-holes)
  - Notifications sent within 10 seconds of failover (previous polling interval)
  - Removed `notify.sh` calls from `keepalived_notify.sh` (Pi-holes only log events)
  - Updated `setup.py` to NOT deploy `notify.sh` and `notify.conf` to Pi-holes
  - Added `send_notification()` function in `monitor.py` with Telegram support
  - **Impact:** Easier to manage, no sync issues, cleaner separation of concerns
  - Updated files:
    - `keepalived/scripts/keepalived_notify.sh` - removed notify.sh calls
    - `setup.py` deploy_keepalived_remote() - removed notify.sh/conf deployment
    - `dashboard/monitor.py` - added send_notification() and failover notifications

---

## [0.10.0-beta.17] - 2025-12-06

### 🐛 Fixed

#### Keepalived Deployment
- **Fixed missing notification infrastructure on Pi-holes:**
  - **Issue:** Failover events were detected but no Telegram/Discord/Pushover notifications were sent
  - **Root cause:** `notify.sh` script was not deployed to Pi-holes, `/etc/pihole-sentinel/` directory didn't exist
  - Creates `/etc/pihole-sentinel/` directory on Pi-holes during deployment
  - Deploys `notify.sh` script to `/usr/local/bin/` (required by keepalived_notify.sh)
  - Deploys `notify.conf` template to `/etc/pihole-sentinel/` (placeholder for user credentials)
  - Sets proper permissions (755 for directory, 644 for notify.conf, 755 for notify.sh)
  - **Impact:** Notifications now work correctly when failover events occur
  - **Note:** Users must configure notification credentials via web interface
  - Updated `setup.py` deploy_keepalived_remote() function (lines 1082-1086, 1102-1103, 1124, 1131-1133)

---

## [0.10.0-beta.16] - 2025-12-06

### ✨ Improved

#### Setup Script
- **Added pre-deployment directory and file checks:**
  - Creates `/etc/pihole-sentinel` directory before systemd service starts
  - **Prevents:** systemd NAMESPACE error (`Failed to set up mount namespacing: /etc/pihole-sentinel: No such file or directory`)
  - Deploys VERSION file to `/opt/VERSION` (correct location for monitor.py to read)
  - Sets proper ownership (pihole-monitor:pihole-monitor) and permissions (755/644)
  - **Impact:** Robust deployment that prevents common systemd mount namespace failures
  - Updated `setup.py` deploy_monitor_remote() function (lines 902-906, 921, 953, 982-984)

---

## [0.10.0-beta.15] - 2025-12-06

### 🐛 Fixed

#### Monitor Service
- **Fixed notification settings save error (500 Internal Server Error):**
  - **Issue:** Settings page returned "Failed to save settings" with HTTP 500 error
  - **Root cause:** systemd's `ProtectSystem=strict` made `/etc/` read-only for the service
  - Added `/etc/pihole-sentinel` to `ReadWritePaths` in systemd service file
  - Added detailed error logging with stack traces for easier debugging
  - **Impact:** Notification settings (Telegram, Discord, Pushover, etc.) can now be saved via web interface
  - Updated `systemd/pihole-monitor.service` (line 20)
  - Updated `dashboard/monitor.py` (line 824) to log save errors with full traceback

---

## [0.10.0-beta.14] - 2025-12-05

### ✨ Improved

#### Setup Script
- **Improved network interface selection UX:**
  - Filters out virtual interfaces (docker, veth*, br-*, tailscale*, etc.)
  - Shows only physical network interfaces by default
  - Prioritizes common interface names (eth0, ens18, enp3s0, eno1)
  - Numbered list display with max 5 interfaces shown
  - Colorized output with clear default indication
  - Better confirmation prompt for non-standard interfaces
  - **Impact:** Much clearer interface selection, especially on systems with many virtual interfaces
  - Fixed issue where docker-debian showed 12+ interfaces (mostly virtual)

---

## [0.10.0-beta.13] - 2025-12-05

### 🐛 Fixed

#### Setup Script
- **Fixed Python version compatibility in setup.py:**
  - Replaced hardcoded `python3.11-dev` and `python3.11-venv` with generic `python3-dev` and `python3-venv`
  - **Issue:** Setup failed on systems with Python 3.13+ (Debian Trixie, Ubuntu 24.10+)
  - **Root cause:** Hardcoded version-specific package names in setup.py and system-requirements.txt
  - Updated both `setup.py` (lines 240-242) and `system-requirements.txt` (lines 3, 9)
  - **Impact:** Setup now works on any Python 3.8+ system regardless of exact version
  - Tested on Python 3.13.5 (Debian Trixie)

---

## [0.10.0-beta.12] - 2025-12-05

### 🐛 Fixed

#### Monitor Service
- **Improved FTL auth timeout and error logging:**
  - Increased auth API timeout from 5 to 10 seconds to handle slower responses
  - **Issue:** After Trixie upgrade on pihole2, occasional "Server disconnected" errors
  - **Root cause:** FTL auth requests timing out under load or during restarts
  - Improved error logging from debug to warning level
  - Added exception class name to error messages for better debugging
  - **Impact:** Fewer false "Pi-hole service down" alerts during normal operation
  - Helps diagnose intermittent connectivity issues with pihole2

---

## [0.10.0-beta.11] - 2025-12-05

### 🐛 Fixed

#### Monitor Dashboard
- **Fixed timezone display for all users regardless of location:**
  - Dashboard showed UTC timestamps, causing confusion for users in different timezones
  - **Solution:** Frontend now converts UTC to browser's local timezone automatically
  - Database stores timestamps in UTC (universal standard)
  - JavaScript adds ' UTC' suffix and converts to user's local time
  - Works automatically for any timezone without server configuration
  - **Impact:** Dutch users see CET/CEST, US users see EST/PST, etc.
  - Changed 7 timestamp conversions in index.html:
    - Last update display (line 792)
    - Chart labels (line 980)
    - Failover event times (lines 1064, 1067, 1090)
    - Event list times (line 1111)
  - **Best practice:** UTC in database, local display in browser

---

## [0.10.0-beta.10] - 2025-11-17

### 🐛 Fixed

#### CI/CD Workflows
- **Made PR comment step optional in enforce-merge-direction workflow:**
  - Added `continue-on-error: true` to comment posting step
  - Workflow now succeeds even if repository-level permissions block PR comments
  - Core merge direction check still enforces rules correctly
  - **Root cause:** Repository workflow permissions set to "Read" instead of "Read and write"
  - **Workaround:** Comment step failures no longer fail the entire workflow
  - **To enable comments:** Settings → Actions → General → Workflow permissions → "Read and write"
  - Merge direction enforcement is functional, comments are optional enhancement

---

## [0.10.0-beta.9] - 2025-11-17

### 🐛 Fixed

#### CI/CD Workflows
- **Added missing permissions to enforce-merge-direction workflow:**
  - Workflow failed with "Resource not accessible by integration" (HTTP 403)
  - Added `permissions` block with `pull-requests: write` and `issues: write`
  - GitHub Actions token now has permission to post PR comments
  - Workflow can now successfully complete both check and comment steps
  - Error occurred in step 2 (Add merge direction comment) due to missing permissions

---

## [0.10.0-beta.8] - 2025-11-17

### 🐛 Fixed

#### CI/CD Workflows
- **Fixed critical YAML syntax error in enforce-merge-direction workflow:**
  - JavaScript template literals (backticks) in `script:` section caused YAML parser conflict
  - Converted template literals to string concatenation for YAML compatibility
  - Workflow was completely non-functional due to syntax error (never triggered on PRs)
  - **Impact:** Merge direction enforcement now works correctly
  - **Root cause:** Line 111-120 had invalid YAML syntax preventing workflow execution
  - Validated fix with Python YAML parser - syntax now correct
  - Required check can now be added to branch protection rules after workflow runs

### 🔧 Improved

#### Developer Experience
- Merge direction enforcement workflow will now trigger on pull requests
- GitHub Actions will recognize the check after first successful run
- Can be added as required status check in branch protection settings

---

## [0.10.0-beta.7] - 2025-11-17

### 🐛 Fixed

#### Code Quality
- **Fixed Python SyntaxWarning in setup.py:**
  - Fixed invalid escape sequence warning in `escape_for_sed()` docstring (line 137)
  - Changed docstring to raw string (r"""...""") to properly handle backslash documentation
  - No functional changes, purely cosmetic fix for Python 3.12+ compatibility

#### Test Infrastructure
- **Improved security scan accuracy:**
  - Reduced false positives in `run-security-scans.sh`
  - Now correctly excludes safe patterns: `getpass()`, `.get()`, function parameters
  - Excludes template strings like `PRIMARY_PASSWORD={...}`
  - Fixed grep regex errors with unmatched braces
  - Security scan now reports "✓ No hardcoded secrets found" instead of warnings on safe code

### 🔧 Improved

#### Developer Experience
- Test suite now runs cleanly without warnings or false positives
- More accurate security feedback for developers
- Better distinction between actual security issues and safe password handling

---

## [0.10.0-beta.6] - 2025-11-17

### ✨ New

#### Test Automation Infrastructure
- **Implemented complete test automation script suite:**
  - Created `.github/scripts/` directory with 8 automated test scripts
  - **`run-syntax-checks.sh`** - Validates Python and Bash syntax across codebase
  - **`run-quality-checks.sh`** - Checks code quality (print statements, line endings, required files)
  - **`run-security-scans.sh`** - Scans for hardcoded secrets and file permission issues
  - **`test-failover.sh`** - Automated failover testing with VIP transition timing
  - **`test-dashboard.sh`** - Dashboard API endpoint validation with JSON response verification
  - **`generate-test-summary.sh`** - Generates test summaries from test reports
  - **`nightly-tests.sh`** - Nightly automated test execution with email notifications
  - **`run-all-tests.sh`** - Master script to run all automated tests sequentially
  - All scripts are executable (755 permissions) and follow bash best practices

### 🔧 Improved

#### Testing Workflow
- **Closed gap between documentation and implementation:**
  - CLAUDE.md and TEST_AUTOMATION_GUIDE.md extensively documented these scripts
  - Scripts were referenced throughout testing documentation but were not implemented
  - Now fully functional and tested - `run-all-tests.sh` successfully validates codebase

#### Developer Experience
- Developers can now run automated tests locally before pushing
- CI/CD pipelines can use these scripts for automated quality gates
- Nightly testing can be scheduled via cron for continuous validation
- Test reports can be automatically generated and summarized

### 📚 Documentation
- Scripts match exact specifications in TEST_AUTOMATION_GUIDE.md (lines 131-675)
- All usage examples in documentation are now executable
- Testing workflow is fully operational and reproducible

---

## [0.10.0-beta.5] - 2025-11-17

### 📚 Documentation

#### Git Workflow Rules for AI Assistants
- **Added "Critical: Always Push Changes (Git Workflow)" mandatory rule to CLAUDE.md:**
  - Explicitly requires pushing all changes to GitHub before ending any session
  - Prevents lost work due to AI sandbox being temporary and isolated
  - Includes session end checklist to verify all changes are pushed
  - Emphasizes that GitHub is the only way to transfer work from AI to user
  - Provides examples of correct vs incorrect workflow
  - **Addresses critical issue** where unpushed changes are lost when sandbox closes

- **Added "Required: Provide Git Commands for Learning" rule to CLAUDE.md:**
  - Requires AI to show exact git commands used during work
  - Helps user learn git through repeated exposure and practice
  - Includes command explanations and what they do
  - Always provides pull commands after pushing
  - Lists common git command categories with examples
  - **Supports user's learning journey** with git workflow

#### Cleanup
- **Verified removal of private reference files:**
  - Confirmed no references to `ai-versioning-instructions.md`
  - Confirmed no references to Dutch quick reference guides
  - These files were already removed in previous commits (3004b82)
  - Only harmless mentions remain in audit report documenting past state

### 🔧 Improved

#### Developer Experience
- Better transparency in git operations through required command display
- Reduced risk of lost work through mandatory push requirements
- Enhanced learning through educational git command explanations
- Clearer workflow expectations for AI assistants

---

## [0.10.0-beta.4] - 2025-11-16

### 📚 Documentation

#### Development Environment Clarity
- **Added "Critical: Development Environment Awareness" mandatory rule to CLAUDE.md:**
  - Explicitly defines AI sandbox environment (`/home/user/pihole-sentinel/`)
  - Explicitly defines user's local environment (`~/Workspace/pihole-sentinel/`)
  - Clarifies GitHub as the only connection/sync point between environments
  - Provides clear communication rules: AI should never instruct user to work in `/home/user/pihole-sentinel/`
  - Defines workflow protocol: AI makes changes and commits, user pulls and reviews locally
  - Includes examples of correct vs incorrect communication
  - **Addresses recurring miscommunication issue** where AI forgets we work in separate environments

### 🔧 Improved

#### Communication Protocol
- AI assistants now have explicit guidelines to avoid confusing path references
- Clear separation of responsibilities: AI does file operations, user does git pull/review
- Better workflow clarity prevents back-and-forth about "where to run commands"

---

## [0.10.0-beta.3] - 2025-11-16

### 🎉 New Features

#### Version Management Enforcement
- **Git Pre-Commit Hook for Version Management:**
  - Added automated pre-commit hook to enforce version management rules
  - Checks that VERSION file is updated for all code changes
  - Checks that CHANGELOG.md is updated for all code changes
  - Validates code quality (no print() statements, no CRLF line endings)
  - Allows documentation-only changes without version updates
  - Template hook available in `.githooks/` directory for easy installation
  - Comprehensive installation guide in `.githooks/README.md`

#### Enhanced AI Assistant Guidelines
- **Mandatory Rules Section in CLAUDE.md:**
  - Added prominent "MANDATORY RULES - READ FIRST" section
  - Explicit version management requirements for every commit
  - Pre-commit verification checklist for AI assistants
  - Clear failure protocol for non-compliance
  - Mandatory commit message format with version reference

### 🔧 Improved

#### Documentation
- **Development Workflows:**
  - Added "Initial Development Setup" section with git hook installation
  - Clear instructions for testing the pre-commit hook
  - Updated Table of Contents to reference mandatory rules

#### Code Quality
- **Automated Quality Gates:**
  - Prevents commits without proper versioning
  - Enforces logging best practices (no print() in production code)
  - Ensures Unix line endings (LF) in bash scripts
  - Provides clear error messages and remediation steps

### 📚 Documentation

- Added `.githooks/README.md` with hook installation and usage guide
- Updated CLAUDE.md with mandatory version management rules
- Added Development Workflows setup instructions
- Documented commit message format requirements
- **Merged Comprehensive Audit & Test Infrastructure from develop:**
  - Added `AUDIT_REPORT_20251116.md` with complete code quality assessment (Score: 89/100 - Excellent)
  - Added `.github/TEST_AUTOMATION_GUIDE.md` (700 lines) for automated test execution and CI/CD integration
  - Added `.github/TEST_DOCUMENTATION_TEMPLATE.md` (802 lines) for standardized test reporting
  - Enhanced `CLAUDE.md` with audit status badge and test infrastructure overview section
  - Provides complete quality assurance framework for production readiness

---

## [0.10.0-beta.2] - 2025-11-16

### 🐛 Fixed

#### Code Quality & Security
- **Critical Code Quality Improvements:**
  - Addressed security vulnerabilities identified in audit
  - Fixed potential code injection risks
  - Improved input validation and sanitization
  - Enhanced error handling across codebase

### 📚 Documentation

- **Branch Protection & Workflow:**
  - Added comprehensive branch protection setup guide
  - Created CODEOWNERS file for repository governance
  - Documented branching strategy (main/develop/testing)
  - Clarified branch protection settings for personal vs organization repos
  - Added todo lists and workflow guidance

---

## [0.10.0-beta.1] - 2025-11-15

### ⚠️ Important Changes

#### License Change
- **Changed License from MIT to GPL v3.0:**
  - More appropriate for infrastructure/systems software
  - Ensures contributions remain open source
  - Protects against proprietary forks
  - Aligns with project philosophy

### 📚 Documentation

- **Release Readiness & Repository Setup:**
  - Added comprehensive release readiness audit report
  - Documented GitHub About section configuration
  - Improved repository metadata and discoverability
  - Enhanced project presentation on GitHub

---

## [0.9.0-beta.2] - 2025-11-15

### 🐛 Fixed

#### Documentation Safety
- **Removed Dangerous Production Advice:**
  - Removed 'git pull on production' recommendation from TESTING-GUIDE.md
  - Prevents accidental production system corruption
  - Promotes safer deployment practices

### 🔧 Improved

#### Documentation
- **README Enhancements:**
  - Added comprehensive introduction section
  - Updated version badges to v0.9.0-beta.1
  - Fixed badge version format for consistency
  - Improved project description and value proposition

---

## [0.9.0-beta.1] - 2025-11-14

### 🎉 New Features

#### Automatic API Key Injection
- **Automatic API key configuration during deployment:**
  - Setup script now automatically injects Pi-hole API keys into `index.html`
  - No manual configuration required after deployment
  - Seamless dashboard experience out-of-the-box
  - Secure handling of API credentials during deployment

#### Enhanced Dashboard Features
- **Improved Settings Management:**
  - Settings button repositioned to right side of header for better UX
  - Auto-save notification settings when clicking Test button
  - Better user warnings for unsaved notification settings
  - Fixed masked notification values not being saved correctly
  - Test notifications now use saved settings instead of form values

#### Chart & Visualization Improvements
- **Enhanced Historical Data Display:**
  - Chart.js CDN fallback for better reliability
  - Improved error handling for chart initialization
  - Fixed timestamp timezone issues in charts
  - Better debugging for chart rendering

### 🔧 Improved

#### API Compatibility
- **Enhanced Pi-hole v6 API Support:**
  - Fixed DHCP leases API call with proper `content_type=None`
  - Added fallback to legacy PHP API for DHCP leases count
  - Better handling of API response variations

#### VIP Detection
- **Improved Virtual IP Status:**
  - Enhanced VIP status indicator with conflict detection
  - Better visual feedback for VIP assignment
  - Clearer indication of which node holds the VIP

### 🐛 Fixed

- API key injection now works automatically during deployment
- Masked notification values are properly saved
- Chart.js loads correctly with CDN fallback
- DHCP leases count works with both v6 and legacy APIs
- Settings button placement improved
- Unsaved notification settings warnings work correctly

### 📚 Documentation

- Updated version badges and references
- Documented automatic API key injection feature
- Added deployment notes for new features

---

## [0.8.0] - 2025-11-14

### 🔧 Improved

#### Dependencies

- **Updated Python dependencies to newer, more secure versions:**
  - `fastapi`: 0.68.0 → ≥0.104.0
  - `uvicorn`: 0.15.0 → ≥0.24.0 (with standard extras)
  - `aiohttp`: 3.8.1 → ≥3.9.0
  - `aiosqlite`: 0.17.0 → ≥0.19.0
  - `aiofiles`: 0.8.0 → ≥23.2.0
  - `python-dotenv`: 0.19.0 → ≥1.0.0
  - Added version constraints to root `requirements.txt`

#### Logging & Monitoring

- **Replaced all `print()` statements with proper logging in `monitor.py`:**
  - Added Python `logging` module with configurable levels
  - Logs now written to `/var/log/pihole-monitor.log` (when directory exists)
  - Better debugging with `logger.debug()`, `logger.info()`, `logger.warning()`, `logger.error()`
  - Added `exc_info=True` for better error traceability
  - Console output remains available via StreamHandler

#### Error Handling

- **Improved error handling in `sync-pihole-config.sh`:**
  - Now distinguishes between "file doesn't exist" vs "sync failed" errors
  - Checks if remote file exists before attempting rsync
  - Better error messages for network/permission issues
  - Exits with error on critical sync failures instead of continuing

#### VIP Detection

- **Added retry logic to VIP detection (`check_who_has_vip`):**
  - 3 retry attempts with 1-second delays between failures
  - Better logging of MAC address detection attempts
  - More reliable VIP detection in high-load scenarios
  - Clearer warnings when VIP has no ARP entry

#### Network Configuration

- **Fixed hardcoded network interface in keepalived scripts:**
  - `keepalived_notify.sh` now uses `${INTERFACE}` variable instead of hardcoded `eth0`
  - Reads interface from environment with fallback to `eth0`
  - Supports all network interface types (ens18, enp3s0, etc.)

#### Timezone Configuration

- **Made timezone auto-detection in `setup.py`:**
  - Automatically detects system timezone using `timedatectl`
  - Falls back to `Europe/Amsterdam` if detection fails
  - No longer hardcoded - adapts to system configuration
  - Better logging of configured timezone

### 🐛 Fixed

- Network interface no longer hardcoded in arping command
- VIP detection more reliable with retry mechanism
- Sync errors now properly reported instead of silently ignored
- DHCP configuration errors logged with correct severity
- All exceptions now properly logged with context

### 📚 Documentation

- Added this CHANGELOG.md file
- All changes documented with rationale

### 🔒 Security

- Updated dependencies address known CVEs in older versions
- Better error logging improves security incident detection
- No changes to existing security features

---

## Legend

- 🎉 New feature
- 🔧 Improvement/Enhancement
- 🐛 Bug fix
- 🔒 Security update
- 📚 Documentation
- ⚠️ Breaking change
- 🗑️ Deprecated/Removed
