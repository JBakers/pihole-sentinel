# Pi-hole Sentinel Development Plan

**Last Updated:** 2026-08-31
**Active Branch:** `develop`
**Current Version:** 0.25.8

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
- R11: release automation standardized future tags on `vX.Y.Z`.
- Configurable database retention and automatic daily cleanup are implemented,
  documented, and covered by tests.
- R9: minimal project metadata and aligned Black, isort, Pylint, and Flake8
  configuration are implemented; both linters pass on `develop`.
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

Implemented foundations already covered by automated tests:

- [x] Unit suite passes on the v0.25.5 `develop` baseline: 569 passed and 10
      environment-dependent tests skipped.
- [x] Two-node and three-node Docker harnesses and integration suites exist.
- [x] Database migration and legacy `PRIMARY_*`/`SECONDARY_*` compatibility are
      implemented and covered by automated tests.
- [x] Release automation creates consistent `vX.Y.Z` tags and tarballs.

Remaining release evidence:

- [x] Resolve the existing Pylint and Flake8 debt. Both linters pass on
      `develop` with an explicit project baseline.
- [x] Complete the dependency security scan successfully on `develop`. Python
      and Bash syntax checks, Bandit medium/high checks, `pip check`, and Safety
      pass after patched dependency lower bounds were added. The CI project scan
      uses `SAFETY_API_KEY` when the repository secret is configured.
- [x] Execute and record both two-node and three-node Docker integration suites
      against the release candidate: 18 two-node tests and 8 three-node tests
      passed locally on 2026-08-31.
- [ ] Perform and record an end-to-end upgrade from the current stable legacy
      two-node deployment, including database migration and preservation of
      history and notification settings.
- [ ] Manually test VIP failover and failback across every configured node.
- [ ] Record end-to-end DNS continuity, DHCP ownership, debounce, and paired
      notification behavior during the manual failover scenarios.
- [ ] Record dashboard behavior at desktop and mobile breakpoints with two and
      three nodes.
- [ ] Complete dedicated upgrade, rollback, and uninstall guidance, then audit all
      installation lifecycle documentation against a clean supported host.
- [ ] Add SHA-256 checksums to release artifacts and verify the release workflow,
      version metadata, generated tarballs, and tag against a release candidate.
- [ ] Record an explicit go/no-go decision before the owner promotes `develop` to
      `main` as v1.0.0.

### P1 - Repository Hygiene

- [ ] R4/R8: plan and execute root cleanup without breaking published commands:
      move visual assets under `assets/`, rationalize Docker Compose locations and
      names, and assess moving `sync-pihole-config.sh` under `bin/`.
- [ ] Update every code, workflow, documentation, packaging, and download path in
      the same change as each moved file.
- [x] R9: add a minimal `pyproject.toml` for tool and project metadata.
- [ ] Document or rename `system-requirements.txt` to a conventional, unambiguous
      system dependency filename.

### P2 - Project Maintenance

- [ ] R15: publish and pin a GitHub Discussions welcome post with support and issue
      reporting guidance. This is a manual GitHub task.
- [ ] Decide whether GitHub Pages or another hosted documentation system adds
      enough value to maintain.

### Product Backlog

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
