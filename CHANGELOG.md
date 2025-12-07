# Changelog

All notable changes to Pi-hole Sentinel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.10.0-beta.14] - 2025-12-07

### ✨ New

#### Testing Infrastructure
- **Added comprehensive unit test framework:**
  - Created `tests/` directory with full pytest configuration
  - Added 4 test modules with 100+ test cases:
    - `test_validation.py` - Input validation (IP, interface, port, username)
    - `test_vip_detection.py` - VIP MAC address detection logic
    - `test_api_handlers.py` - Pi-hole API request/response handling
    - `test_dhcp_parsing.py` - DHCP configuration parsing and failover
  - Added `pytest.ini` with coverage configuration (60% minimum threshold)
  - Added `conftest.py` with shared fixtures and test utilities
  - Added `requirements-dev.txt` with development dependencies
  - Added `Makefile` with common development commands
  - Added `tests/README.md` with testing guide and examples
  - **Impact:** Enables automated testing, prevents regressions, improves code quality
  - **Priority:** 🔴 HIGH - Addresses audit recommendation #1

### 🔧 Improved

#### Documentation
- **Enhanced test documentation:**
  - Comprehensive test organization guide
  - Test category markers (unit, integration, slow, network, asyncio)
  - Coverage reporting instructions
  - CI/CD integration examples
  - Debugging and troubleshooting guide

#### Development Workflow
- **Added development tooling:**
  - `make test` - Run all tests with coverage
  - `make test-unit` - Run only unit tests
  - `make lint` - Run code linters
  - `make format` - Format code with black and isort
  - `make clean` - Remove generated files

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
