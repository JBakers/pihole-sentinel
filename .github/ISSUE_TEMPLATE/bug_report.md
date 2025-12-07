---
name: Bug report
about: Create a report to help us improve Pi-hole Sentinel
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description
A clear and concise description of what the bug is.

## Environment
- **Pi-hole Sentinel Version:** [e.g., 0.10.0-beta.15]
- **Pi-hole Version:** [e.g., 6.0]
- **Operating System:** [e.g., Debian 12, Ubuntu 22.04]
- **Python Version:** [e.g., 3.11]
- **Deployment Type:** [Manual / Automated via setup.py]

## Component Affected
- [ ] Monitor Dashboard
- [ ] Keepalived / VRRP
- [ ] DHCP Failover
- [ ] Notifications
- [ ] Configuration Sync
- [ ] Setup Script
- [ ] Other (please specify)

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. Execute command '...'
4. See error

## Expected Behavior
A clear and concise description of what you expected to happen.

## Actual Behavior
A clear and concise description of what actually happened.

## Logs
Please provide relevant log excerpts:

```bash
# Monitor logs
sudo journalctl -u pihole-monitor -n 50

# Keepalived logs
sudo tail -n 50 /var/log/keepalived-notify.log
```

<details>
<summary>Log Output</summary>

```
Paste logs here
```

</details>

## Screenshots
If applicable, add screenshots to help explain your problem.

## Network Configuration
- **Primary IP:** [e.g., 10.10.100.10]
- **Secondary IP:** [e.g., 10.10.100.20]
- **VIP:** [e.g., 10.10.100.2]
- **Network Interface:** [e.g., eth0, ens18]

## Additional Context
Add any other context about the problem here.

## Possible Solution
If you have suggestions on how to fix the bug, please describe them here.
