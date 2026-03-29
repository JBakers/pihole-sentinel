---
name: Bug report
about: Create a report to help us improve Pi-hole Sentinel
title: '[BUG] '
labels: bug
assignees: ''
---

## What happened?
<!-- Describe the bug. Include the exact error message if there is one. -->

## How to reproduce
1.
2.
3.

## Environment
- **PS Version:** <!-- cat /opt/VERSION -->
- **OS:** <!-- e.g. Debian 12 -->
- **Install method:** <!-- setup.py / manual -->
- **Component:** <!-- Setup / Monitor / Keepalived / DHCP / Notifications / Sync -->

## Logs

<details>
<summary>Monitor</summary>

```bash
sudo journalctl -u pihole-monitor -n 50 --no-pager
```

```
paste output here
```

</details>

<details>
<summary>Keepalived</summary>

```bash
sudo systemctl status keepalived
sudo tail -n 50 /var/log/keepalived-notify.log
```

```
paste output here
```

</details>

## Extra info
<!-- Screenshots, network layout, anything else that helps. -->
