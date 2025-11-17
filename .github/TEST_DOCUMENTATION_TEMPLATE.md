# Test Documentation Template

**Purpose:** This template provides a standardized format for documenting all tests executed on the `testing` branch before merging to `main`.

---

## Test Execution Report

**Test Cycle:** [e.g., v0.9.0-beta.2 Testing Cycle]
**Date Started:** [YYYY-MM-DD]
**Date Completed:** [YYYY-MM-DD]
**Tester:** [Name/Team]
**Branch Tested:** `testing`
**Commit Hash:** [git commit hash]
**Environment:** [Development/Staging/Production-like]

---

## Test Environment Setup

### Hardware Specifications

| Server | CPU | RAM | Disk | OS | IP Address |
|--------|-----|-----|------|----|-----------|
| Primary Pi-hole | [e.g., 2 cores] | [e.g., 2GB] | [e.g., 20GB] | [e.g., Debian 12] | [e.g., 10.10.100.10] |
| Secondary Pi-hole | [e.g., 2 cores] | [e.g., 2GB] | [e.g., 20GB] | [e.g., Debian 12] | [e.g., 10.10.100.20] |
| Monitor Server | [e.g., 1 core] | [e.g., 1GB] | [e.g., 10GB] | [e.g., Debian 12] | [e.g., 10.10.100.30] |
| Test Client | [e.g., 1 core] | [e.g., 512MB] | [e.g., 5GB] | [e.g., Ubuntu 24.04] | [e.g., 10.10.100.40] |

### Network Configuration

| Parameter | Value |
|-----------|-------|
| Network | [e.g., 10.10.100.0/24] |
| Gateway | [e.g., 10.10.100.1] |
| VIP | [e.g., 10.10.100.2] |
| Primary IP | [e.g., 10.10.100.10] |
| Secondary IP | [e.g., 10.10.100.20] |
| Monitor IP | [e.g., 10.10.100.30] |
| Interface | [e.g., ens18] |

### Software Versions

| Component | Version | Notes |
|-----------|---------|-------|
| Pi-hole | [e.g., v6.0] | |
| Python | [e.g., 3.11.2] | |
| Keepalived | [e.g., 2.2.8] | |
| SQLite | [e.g., 3.40.1] | |
| Pi-hole Sentinel | [e.g., 0.9.0-beta.2] | |

---

## Test Categories

### ✅ Pre-Merge Checklist

- [ ] All unit tests pass on `develop`
- [ ] Code review completed
- [ ] CHANGELOG.md updated
- [ ] VERSION file updated
- [ ] Documentation updated
- [ ] No known critical bugs

**Notes:**
[Add any relevant notes about pre-merge status]

---

## 1. Setup & Deployment Tests

### 1.1 Fresh Installation Test

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]

**Test Steps:**
1. Clean Debian 12 system prepared
2. Run `sudo python3 setup.py`
3. Follow interactive prompts
4. Verify all services start

**Results:**

| Check | Status | Notes |
|-------|--------|-------|
| Dependencies install | [ ] PASS / [ ] FAIL | |
| Keepalived starts on primary | [ ] PASS / [ ] FAIL | |
| Keepalived starts on secondary | [ ] PASS / [ ] FAIL | |
| Monitor service starts | [ ] PASS / [ ] FAIL | |
| Dashboard accessible | [ ] PASS / [ ] FAIL | |
| VIP on primary | [ ] PASS / [ ] FAIL | |

**Command Output:**
```
[Paste relevant command output or logs]
```

**Issues Found:**
[List any issues, or write "None"]

**Screenshots:**
[Attach screenshots if applicable]

---

### 1.2 Upgrade Test

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]
**Upgraded From:** [e.g., v0.8.0]
**Upgraded To:** [e.g., v0.9.0-beta.2]

**Test Steps:**
1. Install previous version (v0.8.0)
2. Run `git pull && sudo python3 setup.py`
3. Verify configuration migration
4. Check all services restart

**Results:**

| Check | Status | Notes |
|-------|--------|-------|
| Configuration migration works | [ ] PASS / [ ] FAIL | |
| Database schema updates | [ ] PASS / [ ] FAIL | |
| All services restart | [ ] PASS / [ ] FAIL | |
| Backward compatibility | [ ] PASS / [ ] FAIL | |
| Existing settings preserved | [ ] PASS / [ ] FAIL | |

**Issues Found:**
[List any issues, or write "None"]

---

### 1.3 Multi-Platform Test

**Test Matrix:**

| Platform | Python | Result | Tester | Date | Notes |
|----------|--------|--------|--------|------|-------|
| Debian 11 | 3.9 | [ ] PASS / [ ] FAIL / [ ] SKIP | | | |
| Debian 12 | 3.11 | [ ] PASS / [ ] FAIL / [ ] SKIP | | | |
| Ubuntu 22.04 LTS | 3.10 | [ ] PASS / [ ] FAIL / [ ] SKIP | | | |
| Ubuntu 24.04 LTS | 3.12 | [ ] PASS / [ ] FAIL / [ ] SKIP | | | |
| Raspberry Pi OS | 3.11 | [ ] PASS / [ ] FAIL / [ ] SKIP | | | |

**Issues Found:**
[List platform-specific issues, or write "None"]

---

## 2. Core Functionality Tests

### 2.1 DNS Failover Test

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]

**Test Scenario 1: Primary FTL Stop**

| Step | Action | Expected Result | Actual Result | Status |
|------|--------|----------------|---------------|--------|
| 1 | Check VIP location | VIP on primary | | [ ] PASS / [ ] FAIL |
| 2 | `systemctl stop pihole-FTL` on primary | VIP moves to secondary within 5s | | [ ] PASS / [ ] FAIL |
| 3 | `dig @VIP_ADDRESS example.com` | DNS resolution continues | | [ ] PASS / [ ] FAIL |
| 4 | Check dashboard | Shows failover event | | [ ] PASS / [ ] FAIL |
| 5 | `systemctl start pihole-FTL` on primary | VIP returns to primary | | [ ] PASS / [ ] FAIL |

**Metrics:**

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| VIP transition time | < 5s | [e.g., 3.2s] | [ ] PASS / [ ] FAIL |
| DNS query disruption | < 2s | [e.g., 1.8s] | [ ] PASS / [ ] FAIL |
| Failback time | < 10s | [e.g., 8.5s] | [ ] PASS / [ ] FAIL |

**Command Output:**
```bash
# Before failover
$ dig @10.10.100.2 example.com +short
[paste output]

# During failover
$ systemctl stop pihole-FTL
$ dig @10.10.100.2 example.com +short
[paste output]

# After failback
$ systemctl start pihole-FTL
$ dig @10.10.100.2 example.com +short
[paste output]
```

**Issues Found:**
[List any issues, or write "None"]

---

### 2.2 DHCP Failover Test

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP (if DHCP disabled)
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]

**Test Scenario: DHCP State During Failover**

| Step | Action | Expected Result | Actual Result | Status |
|------|--------|----------------|---------------|--------|
| 1 | Check DHCP on primary | Enabled (MASTER) | | [ ] PASS / [ ] FAIL |
| 2 | Check DHCP on secondary | Disabled (BACKUP) | | [ ] PASS / [ ] FAIL |
| 3 | Trigger failover | DHCP disabled on primary, enabled on secondary | | [ ] PASS / [ ] FAIL |
| 4 | Request new DHCP lease | Lease granted by secondary | | [ ] PASS / [ ] FAIL |
| 5 | Check existing leases | Remain valid | | [ ] PASS / [ ] FAIL |

**DHCP Lease Test:**
```bash
# Before failover
$ sudo dhclient -r eth0 && sudo dhclient -v eth0
[paste output showing lease from primary]

# After failover
$ sudo dhclient -r eth0 && sudo dhclient -v eth0
[paste output showing lease from secondary]
```

**Issues Found:**
[List any issues, or write "None"]

---

### 2.3 Monitor Dashboard Test

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]
**Browser:** [e.g., Chrome 120, Firefox 121, Safari 17]

**Dashboard Features:**

| Feature | Status | Notes |
|---------|--------|-------|
| Real-time status updates (10s) | [ ] PASS / [ ] FAIL | |
| Historical graphs render | [ ] PASS / [ ] FAIL | |
| Event timeline displays | [ ] PASS / [ ] FAIL | |
| VIP location accuracy | [ ] PASS / [ ] FAIL | |
| DHCP status reporting | [ ] PASS / [ ] FAIL | |
| Dark mode toggle | [ ] PASS / [ ] FAIL | |
| Mobile responsive layout | [ ] PASS / [ ] FAIL | |

**API Endpoint Tests:**

| Endpoint | Method | Status | Response Time | Notes |
|----------|--------|--------|---------------|-------|
| `/api/status` | GET | [ ] PASS / [ ] FAIL | [e.g., 45ms] | |
| `/api/history` | GET | [ ] PASS / [ ] FAIL | [e.g., 120ms] | |
| `/api/events` | GET | [ ] PASS / [ ] FAIL | [e.g., 80ms] | |
| `/api/notifications/settings` | GET | [ ] PASS / [ ] FAIL | [e.g., 35ms] | |
| `/api/notifications/settings` | POST | [ ] PASS / [ ] FAIL | [e.g., 150ms] | |
| `/api/notifications/test` | POST | [ ] PASS / [ ] FAIL | [e.g., 2.5s] | |

**Issues Found:**
[List any issues, or write "None"]

**Screenshots:**
[Attach dashboard screenshots]

---

### 2.4 Notification Test

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]

**Notification Services:**

| Service | Configured | Test Sent | Received | Latency | Status |
|---------|-----------|-----------|----------|---------|--------|
| Telegram | [ ] Yes / [ ] No | [ ] Yes / [ ] No | [ ] Yes / [ ] No | [e.g., 1.2s] | [ ] PASS / [ ] FAIL |
| Discord | [ ] Yes / [ ] No | [ ] Yes / [ ] No | [ ] Yes / [ ] No | [e.g., 0.8s] | [ ] PASS / [ ] FAIL |
| Pushover | [ ] Yes / [ ] No | [ ] Yes / [ ] No | [ ] Yes / [ ] No | [e.g., 1.5s] | [ ] PASS / [ ] FAIL |
| Ntfy | [ ] Yes / [ ] No | [ ] Yes / [ ] No | [ ] Yes / [ ] No | [e.g., 0.9s] | [ ] PASS / [ ] FAIL |
| Custom Webhook | [ ] Yes / [ ] No | [ ] Yes / [ ] No | [ ] Yes / [ ] No | [e.g., 0.5s] | [ ] PASS / [ ] FAIL |

**Failover Event Notifications:**

| Event Type | Notification Sent | Content Correct | Status |
|------------|-------------------|-----------------|--------|
| MASTER | [ ] Yes / [ ] No | [ ] Yes / [ ] No | [ ] PASS / [ ] FAIL |
| BACKUP | [ ] Yes / [ ] No | [ ] Yes / [ ] No | [ ] PASS / [ ] FAIL |
| FAULT | [ ] Yes / [ ] No | [ ] Yes / [ ] No | [ ] PASS / [ ] FAIL |

**Issues Found:**
[List any issues, or write "None"]

---

## 3. Performance & Load Tests

### 3.1 Load Testing

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]
**Tool:** [e.g., `dnsperf`, custom script]

**Test Configuration:**
- Duration: [e.g., 10 minutes]
- Query Rate: [e.g., 1000 queries/second]
- Query Types: [e.g., A, AAAA, PTR]

**Results:**

| Metric | Baseline | During Load | Threshold | Status |
|--------|----------|-------------|-----------|--------|
| CPU Usage (Primary) | [e.g., 5%] | [e.g., 45%] | < 80% | [ ] PASS / [ ] FAIL |
| Memory Usage (Primary) | [e.g., 200MB] | [e.g., 350MB] | < 1.5GB | [ ] PASS / [ ] FAIL |
| CPU Usage (Monitor) | [e.g., 2%] | [e.g., 8%] | < 50% | [ ] PASS / [ ] FAIL |
| Memory Usage (Monitor) | [e.g., 80MB] | [e.g., 120MB] | < 500MB | [ ] PASS / [ ] FAIL |
| Query Response Time (avg) | [e.g., 15ms] | [e.g., 25ms] | < 100ms | [ ] PASS / [ ] FAIL |
| Query Success Rate | [e.g., 100%] | [e.g., 99.8%] | > 99% | [ ] PASS / [ ] FAIL |

**Database Growth:**

| Duration | Database Size | Growth Rate | Status |
|----------|---------------|-------------|--------|
| Start | [e.g., 5MB] | - | - |
| After 24h | [e.g., 8MB] | [e.g., 3MB/day] | [ ] PASS / [ ] FAIL |
| After 7 days | [e.g., 26MB] | [e.g., 3MB/day] | [ ] PASS / [ ] FAIL |

**Issues Found:**
[List any issues, or write "None"]

---

### 3.2 Failover Speed Test

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]

**Test Runs:** [e.g., 10 failover cycles]

| Run | VIP Transition Time | DNS Disruption | DHCP Failover | Status |
|-----|---------------------|----------------|---------------|--------|
| 1 | [e.g., 3.2s] | [e.g., 1.8s] | [e.g., 4.1s] | [ ] PASS / [ ] FAIL |
| 2 | [e.g., 3.5s] | [e.g., 2.0s] | [e.g., 4.3s] | [ ] PASS / [ ] FAIL |
| 3 | [e.g., 3.1s] | [e.g., 1.7s] | [e.g., 3.9s] | [ ] PASS / [ ] FAIL |
| ... | ... | ... | ... | ... |
| **Average** | [e.g., 3.3s] | [e.g., 1.9s] | [e.g., 4.2s] | |
| **Max** | [e.g., 4.2s] | [e.g., 2.5s] | [e.g., 5.1s] | |
| **Min** | [e.g., 2.8s] | [e.g., 1.5s] | [e.g., 3.5s] | |

**Thresholds:**
- VIP Transition: < 5s
- DNS Disruption: < 3s
- DHCP Failover: < 10s

**Overall Status:** [ ] PASS / [ ] FAIL

**Issues Found:**
[List any issues, or write "None"]

---

### 3.3 Network Condition Tests

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]
**Tool:** [e.g., `tc` (traffic control)]

**Latency Test:**

| Latency | VIP Detection | Failover Time | DNS Response | Status |
|---------|---------------|---------------|--------------|--------|
| 0ms (baseline) | [e.g., 200ms] | [e.g., 3.2s] | [e.g., 15ms] | [ ] PASS / [ ] FAIL |
| 50ms | [e.g., 250ms] | [e.g., 3.8s] | [e.g., 65ms] | [ ] PASS / [ ] FAIL |
| 100ms | [e.g., 300ms] | [e.g., 4.5s] | [e.g., 115ms] | [ ] PASS / [ ] FAIL |
| 200ms | [e.g., 400ms] | [e.g., 5.2s] | [e.g., 215ms] | [ ] PASS / [ ] FAIL |

**Packet Loss Test:**

| Packet Loss | VIP Detection Success Rate | Failover Success | Status |
|-------------|----------------------------|------------------|--------|
| 0% (baseline) | [e.g., 100%] | [e.g., 100%] | [ ] PASS / [ ] FAIL |
| 1% | [e.g., 98%] | [e.g., 100%] | [ ] PASS / [ ] FAIL |
| 5% | [e.g., 92%] | [e.g., 95%] | [ ] PASS / [ ] FAIL |
| 10% | [e.g., 85%] | [e.g., 90%] | [ ] PASS / [ ] FAIL |

**Issues Found:**
[List any issues, or write "None"]

---

## 4. Security Tests

### 4.1 Authentication Test

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]

**API Authentication:**

| Test | Method | Expected | Actual | Status |
|------|--------|----------|--------|--------|
| Access `/api/status` without API key | GET | 403 Forbidden | | [ ] PASS / [ ] FAIL |
| Access `/api/status` with invalid key | GET | 403 Forbidden | | [ ] PASS / [ ] FAIL |
| Access `/api/status` with valid key | GET | 200 OK | | [ ] PASS / [ ] FAIL |
| Brute force API key (100 attempts) | GET | Rate limited | | [ ] PASS / [ ] FAIL |

**SSH Key Authentication:**

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| SSH to primary with key | Success | | [ ] PASS / [ ] FAIL |
| SSH to secondary with key | Success | | [ ] PASS / [ ] FAIL |
| SSH to monitor with key | Success | | [ ] PASS / [ ] FAIL |
| SSH with password (should fail) | Denied | | [ ] PASS / [ ] FAIL |

**File Permissions:**

| File | Expected | Actual | Status |
|------|----------|--------|--------|
| `/etc/keepalived/.env` | `600 root:root` | | [ ] PASS / [ ] FAIL |
| `/opt/pihole-monitor/.env` | `600 pihole-monitor:pihole-monitor` | | [ ] PASS / [ ] FAIL |
| `/etc/keepalived/keepalived.conf` | `644 root:root` | | [ ] PASS / [ ] FAIL |

**Command:**
```bash
ls -la /etc/keepalived/.env
ls -la /opt/pihole-monitor/.env
ls -la /etc/keepalived/keepalived.conf
```

**Issues Found:**
[List any issues, or write "None"]

---

### 4.2 Input Validation Test

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]

**Injection Attack Tests:**

| Attack Type | Input | Expected | Actual | Status |
|-------------|-------|----------|--------|--------|
| SQL Injection | `'; DROP TABLE events; --` | Rejected/Sanitized | | [ ] PASS / [ ] FAIL |
| Command Injection | ``; rm -rf /`` | Rejected/Sanitized | | [ ] PASS / [ ] FAIL |
| XSS | `<script>alert('XSS')</script>` | Escaped/Sanitized | | [ ] PASS / [ ] FAIL |
| Path Traversal | `../../etc/passwd` | Rejected | | [ ] PASS / [ ] FAIL |

**Issues Found:**
[List any issues, or write "None"]

---

### 4.3 Network Security Test

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]

**CORS Policy:**

| Origin | Endpoint | Expected | Actual | Status |
|--------|----------|----------|--------|--------|
| `http://localhost:8080` | `/api/status` | Allowed | | [ ] PASS / [ ] FAIL |
| `http://127.0.0.1:8080` | `/api/status` | Allowed | | [ ] PASS / [ ] FAIL |
| `http://evil.com` | `/api/status` | Blocked | | [ ] PASS / [ ] FAIL |

**VRRP Authentication:**

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Keepalived uses auth password | Yes | | [ ] PASS / [ ] FAIL |
| Password length | 32 chars | | [ ] PASS / [ ] FAIL |
| Password randomness | High entropy | | [ ] PASS / [ ] FAIL |

**Issues Found:**
[List any issues, or write "None"]

---

## 5. Edge Cases & Error Handling

### 5.1 Network Failure Scenarios

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]

**Scenario Matrix:**

| Scenario | Expected Behavior | Actual Behavior | Status |
|----------|------------------|-----------------|--------|
| Both Pi-holes offline | Monitor shows offline, no VIP | | [ ] PASS / [ ] FAIL |
| Monitor offline | Pi-holes continue failover | | [ ] PASS / [ ] FAIL |
| Split-brain (both MASTER) | Detection & alert | | [ ] PASS / [ ] FAIL |
| VIP on wrong host | Detection & alert | | [ ] PASS / [ ] FAIL |
| ARP table not populating | Retry logic (3x) | | [ ] PASS / [ ] FAIL |

**Issues Found:**
[List any issues, or write "None"]

---

### 5.2 Configuration Error Handling

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]

**Error Scenarios:**

| Scenario | Expected | Actual | Status |
|----------|----------|--------|--------|
| Invalid Pi-hole password | Clear error message | | [ ] PASS / [ ] FAIL |
| Invalid IP address | Validation fails | | [ ] PASS / [ ] FAIL |
| Missing .env variable | Clear error message | | [ ] PASS / [ ] FAIL |
| Corrupt database | Recovery/restore | | [ ] PASS / [ ] FAIL |

**Issues Found:**
[List any issues, or write "None"]

---

### 5.3 Service Failure Handling

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]

**Failure Scenarios:**

| Scenario | Expected | Actual | Status |
|----------|----------|--------|--------|
| Monitor service crash | Systemd restart | | [ ] PASS / [ ] FAIL |
| Keepalived service crash | Systemd restart | | [ ] PASS / [ ] FAIL |
| Database lock | Retry logic | | [ ] PASS / [ ] FAIL |
| API timeout | Graceful failure | | [ ] PASS / [ ] FAIL |

**Command:**
```bash
# Test systemd restart
sudo systemctl stop pihole-monitor
sleep 5
sudo systemctl status pihole-monitor
```

**Issues Found:**
[List any issues, or write "None"]

---

## 6. Documentation Verification

### 6.1 README.md Walkthrough

**Status:** [ ] PASS / [ ] FAIL / [ ] SKIP
**Tested On:** [YYYY-MM-DD]
**Tester:** [Name]

**Installation Steps:**

| Step | Command/Action | Expected | Actual | Status |
|------|----------------|----------|--------|--------|
| 1 | Clone repository | Success | | [ ] PASS / [ ] FAIL |
| 2 | Run setup.py | Success | | [ ] PASS / [ ] FAIL |
| 3 | Access dashboard | Dashboard loads | | [ ] PASS / [ ] FAIL |
| 4 | Test failover | VIP moves | | [ ] PASS / [ ] FAIL |

**Link Verification:**

| Link | Destination | Status | Notes |
|------|-------------|--------|-------|
| [Link text] | [URL] | [ ] Valid / [ ] Broken | |

**Screenshot Accuracy:**

| Screenshot | Current UI Match | Status |
|------------|------------------|--------|
| Dashboard | [ ] Yes / [ ] No | [ ] PASS / [ ] FAIL |
| Settings | [ ] Yes / [ ] No | [ ] PASS / [ ] FAIL |

**Issues Found:**
[List any issues, or write "None"]

---

### 6.2 Other Documentation

**CLAUDE.md:**

| Section | Verified | Issues | Status |
|---------|----------|--------|--------|
| Architecture diagram | [ ] Yes / [ ] No | | [ ] PASS / [ ] FAIL |
| File paths correct | [ ] Yes / [ ] No | | [ ] PASS / [ ] FAIL |
| Code examples work | [ ] Yes / [ ] No | | [ ] PASS / [ ] FAIL |
| Commands tested | [ ] Yes / [ ] No | | [ ] PASS / [ ] FAIL |

**DEVELOPMENT.md:**

| Section | Verified | Issues | Status |
|---------|----------|--------|--------|
| Setup instructions | [ ] Yes / [ ] No | | [ ] PASS / [ ] FAIL |
| venv creation | [ ] Yes / [ ] No | | [ ] PASS / [ ] FAIL |
| Dependencies install | [ ] Yes / [ ] No | | [ ] PASS / [ ] FAIL |

**Issues Found:**
[List documentation issues, or write "None"]

---

## 7. Browser Compatibility

### Desktop Browsers

| Browser | Version | Dashboard | Settings | Dark Mode | Responsive | Status |
|---------|---------|-----------|----------|-----------|------------|--------|
| Chrome | [e.g., 120] | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL |
| Firefox | [e.g., 121] | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL |
| Safari | [e.g., 17] | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL |
| Edge | [e.g., 120] | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL |

### Mobile Browsers

| Browser | Device | Version | Dashboard | Settings | Status |
|---------|--------|---------|-----------|----------|--------|
| iOS Safari | [e.g., iPhone 14] | [e.g., iOS 17] | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL |
| Chrome Mobile | [e.g., Pixel 7] | [e.g., Android 14] | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL |
| Firefox Mobile | [e.g., OnePlus 9] | [e.g., Android 13] | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL | [ ] PASS / [ ] FAIL |

**Issues Found:**
[List browser-specific issues, or write "None"]

---

## 8. Regression Tests

### Known Issues from Previous Versions

| Issue | Version | Fix Verified | Status | Notes |
|-------|---------|--------------|--------|-------|
| VIP detection false negatives | v0.7.x | [ ] Yes / [ ] No | [ ] PASS / [ ] FAIL | |
| Hardcoded network interface | v0.7.x | [ ] Yes / [ ] No | [ ] PASS / [ ] FAIL | |
| Print statements instead of logging | v0.7.x | [ ] Yes / [ ] No | [ ] PASS / [ ] FAIL | |
| DHCP misconfiguration detection | v0.6.x | [ ] Yes / [ ] No | [ ] PASS / [ ] FAIL | |
| Timezone detection | v0.8.0 | [ ] Yes / [ ] No | [ ] PASS / [ ] FAIL | |

**Issues Found:**
[List regression issues, or write "None"]

---

## 9. Sign-Off Criteria

**Status:** [ ] MET / [ ] NOT MET

### Criteria Checklist

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

**Blocker Issues:**
[List any issues blocking merge to main, or write "None"]

**Sign-Off:**

| Role | Name | Date | Signature/Approval |
|------|------|------|--------------------|
| Tester | | | |
| Reviewer | | | |
| Maintainer | | | |

---

## 10. Test Summary

### Overall Results

| Category | Tests | Passed | Failed | Skipped | Pass Rate |
|----------|-------|--------|--------|---------|-----------|
| Setup & Deployment | | | | | % |
| Core Functionality | | | | | % |
| Performance & Load | | | | | % |
| Security | | | | | % |
| Edge Cases | | | | | % |
| Documentation | | | | | % |
| Browser Compatibility | | | | | % |
| Regression | | | | | % |
| **TOTAL** | | | | | **%** |

### Critical Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Overall Pass Rate | ≥ 95% | [e.g., 97%] | [ ] MET / [ ] NOT MET |
| Failover Time | < 5s | [e.g., 3.3s avg] | [ ] MET / [ ] NOT MET |
| DNS Disruption | < 3s | [e.g., 1.9s avg] | [ ] MET / [ ] NOT MET |
| Critical Bugs | 0 | [e.g., 0] | [ ] MET / [ ] NOT MET |
| Security Issues | 0 | [e.g., 0] | [ ] MET / [ ] NOT MET |

### Bug Summary

**Critical Bugs:** [count]
**High Priority Bugs:** [count]
**Medium Priority Bugs:** [count]
**Low Priority Bugs:** [count]

**Bug List:**
1. [Bug title] - Priority: [Critical/High/Medium/Low] - Status: [Open/Fixed/Won't Fix]
2. ...

---

## 11. Recommendations

### Before Merge to Main

**Must Do:**
1. [List critical actions required before merge]
2. ...

**Should Do:**
3. [List recommended actions]
4. ...

**Nice to Have:**
5. [List optional improvements]
6. ...

### For Future Releases

1. [List improvements for next version]
2. ...

---

## 12. Appendix

### Test Environment Details

**Network Diagram:**
```
[ASCII art or description of network topology]
```

**Log Files:**
- [Attach or link to relevant log files]

**Configuration Files:**
- [Attach or link to test configuration files]

### Test Scripts Used

```bash
#!/bin/bash
# Example test script
[Include any custom test scripts used]
```

### Performance Data

**Graphs/Charts:**
[Attach performance graphs if available]

**Raw Data:**
```
[Include raw performance data or link to data files]
```

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| [YYYY-MM-DD] | 1.0 | [Name] | Initial test execution |
| [YYYY-MM-DD] | 1.1 | [Name] | Re-test after bug fixes |

---

**Test Report Completed:** [YYYY-MM-DD]
**Report Approved By:** [Name]
**Next Steps:** [e.g., Merge to main, Create release tag, Deploy to production]
