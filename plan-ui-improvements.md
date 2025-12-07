# UI Improvements Plan - Pi-hole Sentinel

**Status:** In Progress
**Branch:** testing
**Version:** v0.12.0-beta.1

## Completed ✅

### 1. Nightmode Color Consistency
- [x] Fixed nightmode colors between settings.html and index.html
- [x] Applied consistent dark mode background: `linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)`
- [x] Card backgrounds in dark mode: `#0f3460`
- [x] Both pages now use identical dark mode styling

### 2. Version Display Fix
- [x] Fixed version display in settings.html showing v0.0.0
- [x] Updated hardcoded fallback version to v0.12.0-beta.1
- [x] Version now displays correctly in both light and dark mode

### 3. Light Mode Colors - Softer for Eyes
- [x] Changed all white backgrounds to softer grey: `rgba(226, 232, 240, 0.95)`
- [x] Updated borders to subtle grey: `rgba(203, 213, 225, 0.6)`
- [x] Applied to:
  - Header (index.html & settings.html)
  - Node cards (index.html)
  - Chart cards (index.html)
  - Events cards (index.html)
  - Settings cards (settings.html)
  - Modal popup (settings.html)
- [x] Much easier on the eyes in light mode

### 4. Docker Test Environment
- [x] Created Docker Compose setup (frontend: nginx, backend: FastAPI)
- [x] Setup script: `tmp/testing-docker/setup-test-env.sh`
- [x] Automated patching of API_BASE and API_KEY
- [x] CORS configuration for Docker ports
- [x] Test environment isolated from production (in .gitignore)

### 5. Modal Popup Dark Mode
- [x] Fixed message templates popup dark mode styling
- [x] Consistent with rest of settings page

## In Progress 🔄

None currently.

## Completed ✅ (continued)

### 6. Text and Translation Fixes in settings.html
- [x] Reviewed all text strings (excellent quality overall)
- [x] Fixed "Repeat interval" → "Repeat Interval" (consistency)
- [x] Fixed "POST'ed" → "posted" (proper grammar)
- [x] Verified all placeholder text and help text
- [x] Confirmed proper English grammar throughout

## Completed ✅ (continued)

### 7. Remote Install Progress Indicator
- [x] Added progress bars for file copying in deploy_monitor_remote()
- [x] Added progress bars for file copying in deploy_keepalived_remote()
- [x] Added progress indicator for virtual environment creation
- [x] Added progress indicator for Python package installation (with time estimate)
- [x] Shows real-time percentage and filename during file transfers
- [x] Visual progress bars using Unicode block characters (░ and █)

## To Do 📋

### Future Improvements (Optional)
- [ ] Show progress for:
  - SSH key distribution
  - Package installation
  - Service configuration
  - File deployment
- [ ] Visual feedback for user

## Notes

- All changes tested in Docker environment
- Dark mode uses blue gradient background
- Light mode uses soft grey for reduced eye strain
- Version v0.12.0-beta.1 consistent across all pages

## Commit History

- `c1a0550` - style(ui): softer light mode colors and consistent dark mode
