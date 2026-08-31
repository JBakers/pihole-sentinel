# Container Architecture Proof of Concept

## Status

The container sidecar experiment is archived and is not part of the active v1.0
release path. Its exact Git history is preserved by the annotated tag
`archive/container-architecture-poc-2026-08-31`.

## Proven Components

- A Sentinel node container can run keepalived beside a Pi-hole container.
- The sync agent exposes health, state, gravity sync, and sync status endpoints.
- The Docker Compose proof of concept demonstrated VRRP election and VIP movement.

## Open Design Work

- Complete the containerized web installer.
- Define production networking, capabilities, persistence, and upgrade behavior.
- Threat-model sync authentication and secret distribution.
- Add multi-node container integration and failure-recovery tests.
- Decide whether the sidecar architecture replaces or complements bare-metal mode.

## Resuming Work

Create a new feature branch from the archive tag rather than restoring the old
long-lived branch:

```bash
git switch -c feature/container-architecture-v2 \
  archive/container-architecture-poc-2026-08-31
```

Rebase or selectively port the proof-of-concept work onto the then-current
`develop` branch after its architecture has been reviewed.
