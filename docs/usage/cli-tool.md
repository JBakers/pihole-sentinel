# Pi-hole Sentinel CLI Tool Usage

The `pisen` CLI tool provides convenient commands for managing your Pi-hole Sentinel
High Availability setup. It is installed to `/usr/local/bin/pisen` during deployment.

## Commands

| Command | Description |
|---------|-------------|
| `pisen status` | Show service status (monitor + keepalived) |
| `pisen logs` | Tail monitor service logs (live) |
| `pisen vip` | Check VIP location (which node is MASTER) |
| `pisen dashboard` | Show dashboard access URL and monitor IP |
| `pisen health` | Comprehensive health check of all components |
| `pisen test` | Interactive failover testing guide |
| `pisen --version` | Show installed version |
| `pisen --help` | Show help |

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
```

## Installation

The CLI tool is deployed automatically by `setup.py`. To install manually:

```bash
sudo cp bin/pisen /usr/local/bin/pisen
sudo chmod +x /usr/local/bin/pisen
```

## See Also

- [Quick Start Guide](../installation/quick-start.md)
- [API Documentation](../api/README.md)