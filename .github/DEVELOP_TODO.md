# Develop Branch - Todo List

**Last Updated:** 2025-11-16
**Branch:** `develop`
**Purpose:** Active development branch for new features and improvements

---

## Current Sprint

### High Priority

- [ ] **Security Audit**
  - [ ] Review all authentication mechanisms
  - [ ] Audit SSH key handling in setup.py
  - [ ] Review Pi-hole password storage and transmission
  - [ ] Check for potential injection vulnerabilities
  - [ ] Review VRRP password generation

- [ ] **Testing Framework**
  - [ ] Set up pytest for Python components
  - [ ] Add unit tests for monitor.py key functions
  - [ ] Add unit tests for setup.py configuration logic
  - [ ] Set up bats for bash script testing
  - [ ] Create CI/CD pipeline for automated testing

- [ ] **Code Quality**
  - [ ] Run linting on all Python files (pylint/flake8)
  - [ ] Run shellcheck on all bash scripts
  - [ ] Fix any remaining hardcoded values
  - [ ] Add type hints to all Python functions
  - [ ] Improve error messages and logging

### Medium Priority

- [ ] **Documentation**
  - [ ] Add API documentation for monitor endpoints
  - [ ] Create troubleshooting guide
  - [ ] Add network diagram to README
  - [ ] Document all environment variables
  - [ ] Create video tutorial for setup

- [ ] **Feature: HTTPS Support**
  - [ ] Add SSL/TLS support to monitor dashboard
  - [ ] Generate self-signed certificates option
  - [ ] Let's Encrypt integration guide
  - [ ] Update documentation

- [ ] **Feature: Email Notifications**
  - [ ] Add SMTP configuration to monitor
  - [ ] Create email templates
  - [ ] Add email settings to dashboard
  - [ ] Test with common providers (Gmail, Outlook)

- [ ] **Dashboard Improvements**
  - [ ] Add export functionality (CSV, JSON)
  - [ ] Add date range selector for history
  - [ ] Improve mobile responsiveness
  - [ ] Add system resource monitoring (CPU, RAM, disk)
  - [ ] Add Pi-hole query statistics

### Low Priority

- [ ] **Performance**
  - [ ] Optimize database queries
  - [ ] Add database cleanup for old history
  - [ ] Implement caching for API responses
  - [ ] Profile Python code for bottlenecks

- [ ] **Feature: Multi-site Support**
  - [ ] Support monitoring multiple HA pairs
  - [ ] Multi-dashboard view
  - [ ] Aggregate statistics

- [ ] **Feature: Backup & Restore**
  - [ ] Automated config backup
  - [ ] One-click restore functionality
  - [ ] Backup to external storage (S3, NFS)

---

## Backlog

### Ideas for Future Versions

- [ ] IPv6 support and testing
- [ ] Prometheus metrics export
- [ ] Grafana dashboard templates
- [ ] Mobile app (iOS/Android)
- [ ] HA monitoring agent (lightweight alternative to dashboard)
- [ ] Integration with Pi-hole Teleporter
- [ ] Automatic Pi-hole version updates
- [ ] Support for 3+ Pi-hole nodes
- [ ] DNS query logging and analysis
- [ ] Anomaly detection and alerting
- [ ] REST API for external integrations
- [ ] Webhook support for events
- [ ] Custom health check scripts
- [ ] Geo-redundancy support

---

## Bug Fixes Needed

- [ ] Fix VIP detection occasional false negatives
- [ ] Improve DHCP misconfiguration detection accuracy
- [ ] Handle network timeouts more gracefully
- [ ] Fix race condition in notify.sh async execution
- [ ] Improve error messages when Pi-hole API changes

---

## Technical Debt

- [ ] Refactor setup.py into modules (too large at 1480 lines)
- [ ] Separate monitor.py into routes, services, and database modules
- [ ] Create shared library for common functions
- [ ] Standardize error handling across all components
- [ ] Add proper logging rotation configuration
- [ ] Remove deprecated API calls
- [ ] Update to FastAPI 0.110+ (check breaking changes)

---

## Dependencies to Update

- [ ] Review and update all Python dependencies
- [ ] Check for security vulnerabilities with `pip audit`
- [ ] Test with Python 3.13
- [ ] Update keepalived to latest stable version
- [ ] Review system package versions

---

## Notes

- Always test changes in staging environment before merging to testing
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Update CHANGELOG.md with all changes
- Keep CLAUDE.md updated with architecture changes
- Run full test suite before merging to testing
- Code review required for security-related changes

---

## Branching Strategy

```
develop (active development)
  ↓
testing (QA and integration testing)
  ↓
main (stable releases only)
```

**Workflow:**
1. Develop new features in feature branches off `develop`
2. Merge completed features back to `develop`
3. When ready for testing, merge `develop` → `testing`
4. Run full test suite on `testing`
5. If tests pass, merge `testing` → `main`
6. Tag releases on `main` branch

---

**Remember:** This is the active development branch. Code here may be unstable. Always merge to `testing` before production deployment.
