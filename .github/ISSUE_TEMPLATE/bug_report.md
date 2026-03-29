---
name: Bug report
about: Create a report to help us improve Pi-hole Sentinel
title: '[BUG] '
labels: bug
assignees: ''
---

## What went wrong?
<!-- Describe what happened. Be specific — "it doesn't work" is not enough. -->

## Environment

| Item | Value |
|------|-------|
| Pi-hole Sentinel Version | <!-- run: cat /opt/VERSION or pisen version --> |
| Pi-hole Version | <!-- run: pihole version --> |
| Operating System | <!-- e.g. Debian 12, Ubuntu 24.04 --> |
| Python Version | <!-- run: python3 --version --> |
| Install method | <!-- setup.py (automated) / manual --> |
| SSH user used during setup | <!-- root / non-root (e.g. david) --> |
| DHCP failover enabled | <!-- yes / no --> |
| Notification channel | <!-- Telegram / Discord / Pushover / Ntfy / webhook / none --> |

## Component

- [ ] Setup script (`setup.py`)
- [ ] Monitor / Dashboard
- [ ] Keepalived / VRRP / VIP failover
- [ ] DHCP failover
- [ ] Notifications
- [ ] Configuration sync
- [ ] `pisen` CLI
- [ ] Other: ___

## Steps to reproduce

1.
2.
3.

## Expected behaviour
<!-- What should have happened? -->

## Actual behaviour
<!-- What actually happened? Include the exact error message if there is one. -->

## Diagnostic output

Run the relevant commands and paste the output below.

**Setup failures** — copy the full terminal output of setup.py, then run:
```bash
# Check SSH connectivity
ssh -i /root/.ssh/id_pihole_sentinel <user>@<host> "echo ok"
```

**Monitor / dashboard issues:**
```bash
sudo systemctl status pihole-monitor
sudo journalctl -u pihole-monitor -n 100 --no-pager
```

**Keepalived / VIP / failover issues:**
```bash
sudo systemctl status keepalived
sudo tail -n 100 /var/log/keepalived-notify.log
ip neigh show          # ARP table — shows who holds the VIP
ip addr show           # Verify VIP is (or isn't) assigned locally
```

**pisen CLI** (if installed):
```bash
pisen status
pisen version
```

<details>
<summary>Output</summary>

```
Paste output here
```

</details>

## Network layout

| | Primary | Secondary | Monitor |
|---|---|---|---|
| IP address | | | |
| Hostname | | | |
| Network interface | | | |
| VIP | | — | — |

<!-- Mark which node currently holds the VIP, if known. -->

## Additional context
<!-- Anything else that might help: recent changes, timing, frequency of occurrence, etc. -->
