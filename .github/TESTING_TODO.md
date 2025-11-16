# Testing Branch - Todo List

**Last Updated:** 2025-11-16
**Branch:** `testing`
**Purpose:** Quality assurance and integration testing before production release

---

## Current Testing Cycle

### Pre-Merge Checklist

Before merging code from `develop` to `testing`:

- [ ] All unit tests pass on `develop`
- [ ] Code review completed
- [ ] CHANGELOG.md updated
- [ ] VERSION file updated (if applicable)
- [ ] Documentation updated
- [ ] No known critical bugs

---

## Integration Tests

### Setup & Deployment

- [ ] **Fresh Installation Test**
  - [ ] Run `setup.py` on clean Debian 12 system
  - [ ] Verify all dependencies install correctly
  - [ ] Check all services start without errors
  - [ ] Verify dashboard accessible
  - [ ] Test with default configuration

- [ ] **Upgrade Test**
  - [ ] Upgrade from previous version (v0.8.0 → current)
  - [ ] Verify configuration migration works
  - [ ] Check database schema updates
  - [ ] Verify all services restart correctly
  - [ ] Test backward compatibility

- [ ] **Multi-Platform Test**
  - [ ] Test on Debian 11
  - [ ] Test on Debian 12
  - [ ] Test on Ubuntu 22.04 LTS
  - [ ] Test on Ubuntu 24.04 LTS
  - [ ] Test on Raspberry Pi OS

### Core Functionality

- [ ] **DNS Failover**
  - [ ] Stop pihole-FTL on primary → verify VIP moves to secondary
  - [ ] Start pihole-FTL on primary → verify VIP returns to primary
  - [ ] Test DNS resolution through VIP during failover
  - [ ] Verify DNS queries continue during transition
  - [ ] Test with `dig` from client machines

- [ ] **DHCP Failover** (if enabled)
  - [ ] Verify DHCP enabled only on MASTER node
  - [ ] Test DHCP lease acquisition during failover
  - [ ] Verify existing leases remain valid
  - [ ] Check DHCP lease synchronization
  - [ ] Test DHCP misconfiguration detection

- [ ] **Monitor Dashboard**
  - [ ] Verify real-time status updates (10s interval)
  - [ ] Check historical graphs render correctly
  - [ ] Test event timeline displays recent events
  - [ ] Verify VIP location detection accuracy
  - [ ] Check DHCP status reporting
  - [ ] Test dark mode toggle
  - [ ] Test mobile responsive layout

- [ ] **Notifications**
  - [ ] Test Telegram notifications
  - [ ] Test Discord webhooks
  - [ ] Test Pushover notifications
  - [ ] Test Ntfy.sh notifications
  - [ ] Test custom webhook
  - [ ] Verify notifications sent on failover events
  - [ ] Test notification settings persistence

### Stress & Performance Tests

- [ ] **Load Testing**
  - [ ] Monitor resource usage under normal load
  - [ ] Test with 1000+ DNS queries/second
  - [ ] Monitor database growth over 7 days
  - [ ] Check memory leaks in monitor service
  - [ ] Verify keepalived stability under load

- [ ] **Failover Speed**
  - [ ] Measure time for VIP transition (target: <5s)
  - [ ] Measure DNS query disruption time
  - [ ] Measure DHCP failover time
  - [ ] Test rapid failover scenarios (flapping)

- [ ] **Network Conditions**
  - [ ] Test with network latency (50ms, 100ms, 200ms)
  - [ ] Test with packet loss (1%, 5%, 10%)
  - [ ] Test across VLANs
  - [ ] Test with network segmentation
  - [ ] Test VIP ARP table population under various conditions

### Security Tests

- [ ] **Authentication**
  - [ ] Verify Pi-hole password handling
  - [ ] Test SSH key authentication
  - [ ] Check file permissions on sensitive files
  - [ ] Verify generated configs cleanup
  - [ ] Test against common injection attacks

- [ ] **Network Security**
  - [ ] Test with firewall rules enabled
  - [ ] Verify VRRP authentication works
  - [ ] Test SSH key distribution security
  - [ ] Check for exposed sensitive endpoints
  - [ ] Review logs for security events

### Edge Cases & Error Handling

- [ ] **Network Scenarios**
  - [ ] Both Pi-holes offline → monitor behavior
  - [ ] Monitor offline → Pi-holes continue failover
  - [ ] Split-brain scenario (both think they're MASTER)
  - [ ] VIP on wrong host → detection and alerting
  - [ ] ARP table not populating → retry logic

- [ ] **Configuration Errors**
  - [ ] Invalid Pi-hole password → error handling
  - [ ] Invalid IP addresses → validation
  - [ ] Missing environment variables → clear error messages
  - [ ] Corrupt database → recovery procedure
  - [ ] Incorrect keepalived config → detection

- [ ] **Service Failures**
  - [ ] Monitor service crash → restart behavior
  - [ ] Keepalived service crash → detection
  - [ ] Database lock errors → retry logic
  - [ ] API timeout handling
  - [ ] Notification service failures

### Documentation Verification

- [ ] **README.md**
  - [ ] Follow installation steps exactly
  - [ ] Verify all commands work as documented
  - [ ] Check all links are valid
  - [ ] Verify screenshots are up-to-date

- [ ] **CLAUDE.md**
  - [ ] Verify architecture diagram matches implementation
  - [ ] Check all file paths are correct
  - [ ] Verify code examples work
  - [ ] Test all documented commands

- [ ] **Other Documentation**
  - [ ] DEVELOPMENT.md - test setup instructions
  - [ ] EXISTING-SETUP.md - verify migration guide
  - [ ] SYNC-SETUP.md - test sync configuration
  - [ ] CHANGELOG.md - verify all changes documented

---

## Regression Tests

### Known Issues from Previous Versions

- [ ] VIP detection false negatives (v0.7.x) - verify fix works
- [ ] Hardcoded network interface (v0.7.x) - verify dynamic detection
- [ ] Print statements instead of logging (v0.7.x) - verify all replaced
- [ ] DHCP misconfiguration detection (v0.6.x) - verify accuracy
- [ ] Timezone detection (v0.8.0) - verify auto-detection works

---

## Browser Compatibility

### Dashboard Testing

- [ ] **Desktop Browsers**
  - [ ] Chrome/Chromium (latest)
  - [ ] Firefox (latest)
  - [ ] Safari (latest)
  - [ ] Edge (latest)

- [ ] **Mobile Browsers**
  - [ ] iOS Safari
  - [ ] Chrome Mobile (Android)
  - [ ] Firefox Mobile

- [ ] **Features to Test**
  - [ ] Real-time updates (WebSocket/polling)
  - [ ] Dark mode toggle
  - [ ] Responsive layout
  - [ ] Settings page form submission
  - [ ] Historical graphs rendering

---

## Sign-Off Criteria

Before merging `testing` → `main`:

- [ ] All integration tests pass
- [ ] No critical or high-severity bugs
- [ ] Performance meets requirements
- [ ] Security audit completed
- [ ] Documentation verified and accurate
- [ ] At least 7 days of stable operation in testing
- [ ] All regression tests pass
- [ ] Browser compatibility confirmed
- [ ] Load tests pass
- [ ] Backup and restore tested
- [ ] Upgrade path tested

---

## Testing Environment Setup

### Recommended Test Environment

```
┌─────────────────────────────────────────┐
│         Testing Network                 │
├─────────────────────────────────────────┤
│                                          │
│  Primary Pi-hole:    10.10.100.10       │
│  Secondary Pi-hole:  10.10.100.20       │
│  VIP:                10.10.100.2        │
│  Monitor:            10.10.100.30       │
│  Test Client:        10.10.100.40       │
│                                          │
│  Network: 10.10.100.0/24                │
│  Gateway: 10.10.100.1                   │
└─────────────────────────────────────────┘
```

### VM/Container Specs

- **Pi-hole Nodes:** 2 CPU cores, 2GB RAM, 20GB disk
- **Monitor:** 1 CPU core, 1GB RAM, 10GB disk
- **Test Client:** 1 CPU core, 512MB RAM, 5GB disk

---

## Bug Tracking

### Current Known Issues

| Priority | Issue | Status | Assigned | ETA |
|----------|-------|--------|----------|-----|
| - | No known issues | - | - | - |

### Resolved in This Cycle

| Issue | Resolution | Tested | Date |
|-------|------------|--------|------|
| - | - | - | - |

---

## Notes

- All tests must be documented with results
- Screenshots required for UI changes
- Performance metrics must be recorded
- Any test failures must be investigated before merge
- Security findings must be addressed immediately
- Keep this document updated with test results

---

## Branching Strategy

```
develop (active development)
  ↓ (merge when ready for QA)
testing (QA and integration testing) ← YOU ARE HERE
  ↓ (merge only after all tests pass)
main (stable releases only)
```

**Workflow:**
1. Code merged from `develop` to `testing`
2. Run all integration tests on `testing`
3. Document test results
4. Fix any bugs found (merge fixes from `develop`)
5. Re-test until all criteria met
6. Sign off and merge `testing` → `main`
7. Tag release on `main` branch

---

**Remember:** This branch is for testing only. Do not develop new features here. All bugs found should be fixed in `develop` and merged back to `testing`.
