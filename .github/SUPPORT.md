# Support

## Documentation

Start here:

- **[Quick Start Guide](../docs/installation/quick-start.md)** — Install Pi-hole Sentinel in minutes
- **[Existing Setup Guide](../docs/installation/existing-setup.md)** — Add Sentinel to an existing Pi-hole HA setup
- **[CLI Reference](../docs/usage/cli-tool.md)** — `pisen` command reference
- **[Sync Guide](../docs/maintenance/sync.md)** — Config and gravity sync

## Getting Help

| Type of question | Where to go |
| ---------------- | ----------- |
| "How do I...?" / general usage | [GitHub Discussions](https://github.com/JBakers/pihole-sentinel/discussions) |
| Bug report (unexpected behavior) | [GitHub Issues](https://github.com/JBakers/pihole-sentinel/issues) |
| Feature request | [GitHub Issues](https://github.com/JBakers/pihole-sentinel/issues) — label `enhancement` |
| Security vulnerability | [Private Security Advisory](https://github.com/JBakers/pihole-sentinel/security/advisories/new) — **not** a public issue |

## Before Opening an Issue

Please check:

1. The [CHANGELOG.md](../CHANGELOG.md) — your issue may already be fixed in a newer version
2. [Existing Issues](https://github.com/JBakers/pihole-sentinel/issues) — avoid duplicates
3. The [docs/](../docs/) folder — the answer may already be documented

When reporting a bug, include:
- Pi-hole version
- Sentinel version (`cat VERSION`)
- Relevant log output from `journalctl -u pihole-monitor` or Docker logs
- Steps to reproduce
