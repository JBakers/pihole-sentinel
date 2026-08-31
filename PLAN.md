# Pi-hole Sentinel Development Plan

**Last Updated:** 2026-08-31
**Active Branch:** `develop`
**Current Version:** 0.25.5

This is the single source of truth for active work, priorities, and future design
work. Completed release details belong in `CHANGELOG.md`; operational guidance
belongs in `CLAUDE.md` and the documentation tree.

## Current Status

Pi-hole Sentinel v0.25.4 has been stable in a production home environment for
several months. Multi-node support is merged into `main`, and `develop` has been
fast-forwarded to the same baseline before this planning cleanup.

Completed milestones:

- M1-P1 through M1-P5: dynamic N-node configuration, normalized database schema,
  node-based monitoring, API responses, dashboard, installer, sync, Docker
  fixtures, and three-node integration tests.
- D2: `dashboard/monitor.py` coverage increased to 71%, above the 60% gate.
- R1: `setup.py` renamed to `install.py` with active references migrated.
- Repository health: security, contributing, code of conduct, and support
  documentation added.
- R12/R13: development test documentation consolidated and hook messages
  standardized in English.
- v0.25.2 through v0.25.4: multi-node failback, naming, history, and failover
  notification defects fixed.

There are no confirmed open product bugs. New defects take priority over the
backlog below.

## Branch and Release Model

- `develop` is the only active development and integration branch.
- Feature and fix branches target `develop` and are deleted after merge.
- Only the repository owner promotes validated `develop` changes to `main`.
- `main` is the stable production and release branch.
- The former `testing` branch is retired. Release candidates are validated from
  `develop` using the release readiness checklist below.

## Active Backlog

### P0 - v1.0 Release Readiness

- [ ] Run the complete unit, lint, syntax, and security suites on `develop`.
- [ ] Run both two-node and three-node Docker integration environments.
- [ ] Validate upgrade from a legacy two-node environment and database migration
  without losing history or notification settings.
- [ ] Validate legacy `PRIMARY_*` and `SECONDARY_*` configuration compatibility.
- [ ] Manually test VIP failover and failback across every configured node.
- [ ] Verify DNS continuity, DHCP ownership, debounce, and paired notifications.
- [ ] Verify dashboard behavior on desktop and mobile with two and three nodes.
- [ ] Audit installation, upgrade, rollback, and uninstall documentation against a
  clean supported host.
- [ ] Verify release artifacts, version metadata, checksums, and `vX.Y.Z` tag naming.
- [ ] Record an explicit go/no-go decision before the owner promotes `develop` to
  `main` as v1.0.0.

### P1 - Repository Hygiene

- [ ] R4/R8: plan and execute root cleanup without breaking published commands:
  move visual assets under `assets/`, rationalize Docker Compose locations and
  names, and assess moving `sync-pihole-config.sh` under `bin/`.
- [ ] Update every code, workflow, documentation, packaging, and download path in
  the same change as each moved file.
- [ ] R9: add a minimal `pyproject.toml` for tool and project metadata.
- [ ] Document or rename `system-requirements.txt` to a conventional, unambiguous
  system dependency filename.

### P2 - Project Maintenance

- [ ] R11: use `vX.Y.Z` consistently for all future tags and release titles.
- [ ] R15: publish and pin a GitHub Discussions welcome post with support and issue
  reporting guidance. This is a manual GitHub task.
- [ ] Decide whether GitHub Pages or another hosted documentation system adds
  enough value to maintain.

### Product Backlog

- [ ] Add configurable database retention and automatic history cleanup.
- [ ] Add a Prometheus-compatible `GET /metrics` endpoint.
- [ ] Evaluate first-class HTTPS/TLS support versus documented reverse proxies.

## Future v2 - Container Sidecar Architecture

The container architecture proof of concept is outside the v1.0 release path.
Its exact history is preserved in the annotated tag
`archive/container-architecture-poc-2026-08-31`; the long-lived feature branch
can therefore be retired.

Before implementation resumes:

- [ ] Review the threat model for sync authentication and secret distribution.
- [ ] Define production networking, Linux capabilities, persistence, and upgrades.
- [ ] Complete the containerized installer design.
- [ ] Add N-node container integration and failure-recovery tests.
- [ ] Decide whether sidecar mode replaces or complements bare-metal deployment.

See `docs/development/container-architecture-poc.md` for proven components, open
design questions, and restoration instructions.

## Completed and Archived Work

Detailed completed work is recorded in `CHANGELOG.md`. Historical audits and
superseded session handovers are intentionally not duplicated here. The former
session tracker was consolidated into this plan on 2026-08-31.

## Working Agreement

1. Select work from this plan and implement it on `develop` or a short-lived
   branch targeting `develop`.
2. Update this plan when scope or status changes.
3. Update `VERSION`, `CHANGELOG.md`, and the `CLAUDE.md` header for code or
   functional workflow changes.
4. Run `make test` and relevant focused checks before requesting a commit.
5. Obtain explicit user approval before every commit and push.
6. Only the repository owner decides when `develop` is ready for `main`.
