# Pi-hole Sentinel CLI Tool Usage

The `pisen` CLI tool provides convenient commands for managing your Pi-hole Sentinel
High Availability setup. It is installed to `/usr/local/bin/pisen` during deployment.

## Commands

| Command | Short | Description |
|---------|-------|-------------|
| `pisen status` | `pisen -s` | Show service status (monitor + keepalived) |
| `pisen logs` | `pisen -l` | Tail monitor service logs (live) |
| `pisen vip` | `pisen -v` | Check VIP location (which node is MASTER) |
| `pisen dashboard` | `pisen -d` | Show dashboard access URL and monitor IP |
| `pisen health` | `pisen -H` | Comprehensive health check of all components |
| `pisen test` | `pisen -t` | Interactive failover testing guide |
| `pisen sync` | `pisen -S` | Show sync status, config, and last run |
| `pisen sync --run` | | Trigger an immediate configuration sync |
| `pisen --version` | | Show installed version |
| `pisen --help` | | Show help |

## Examples

```bash
# Quick status overview
$ pisen status
Monitor service: active (running)
Keepalived (primary): active (running)
Keepalived (secondary): active (running)

# Check which node has the VIP
$ pisen vip
VIP 192.168.1.2 is on: Primary Pi-hole (192.168.1.10)

# Follow monitor logs in real-time
$ pisen logs

# Run health check
$ pisen health
✅ Monitor service: OK
✅ Primary Pi-hole: Online
✅ Secondary Pi-hole: Online
✅ VIP: Active on Primary
✅ DNS: Resolving

# View sync status
$ pisen sync
  ● pihole-sync.timer  → active
  Next run: Wed 2026-04-16 06:00:00

# Trigger immediate sync
$ pisen sync --run
```

## Installation

The CLI tool is deployed automatically by `setup.py`. To install manually:

```bash
sudo cp bin/pisen /usr/local/bin/pisen
sudo chmod +x /usr/local/bin/pisen
```

## See Also

- [Quick Start Guide](../installation/quick-start.md)
- [Configuration Sync](../maintenance/sync.md)
- [API Documentation](../api/README.md)