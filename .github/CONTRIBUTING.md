# Contributing to Pi-hole Sentinel

Thank you for your interest in contributing! This document covers everything you need to get started.

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Branch Naming](#branch-naming)
- [Commit Convention](#commit-convention)
- [Test Requirements](#test-requirements)
- [PR Checklist](#pr-checklist)

---

## Development Environment Setup

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/pihole-sentinel.git
cd pihole-sentinel

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Run the unit test suite to verify your setup
make test
```

For Docker integration tests:

```bash
make docker-up          # Start mock Pi-hole environment
make docker-integration # Run integration tests
make docker-down        # Tear down
```

---

## Branch Naming

| Type    | Pattern                     | Example                      |
| ------- | --------------------------- | ---------------------------- |
| Feature | `feature/<short-name>`      | `feature/metrics-export`     |
| Bug fix | `fix/<short-description>`   | `fix/dns-latency-null-crash` |
| Docs    | `docs/<short-description>`  | `docs/update-installation`   |
| Chore   | `chore/<short-description>` | `chore/update-dependencies`  |

**Branch flow:** `feature/*` -> `develop` -> `main`

Open normal contribution pull requests against `develop`. Only the repository
owner promotes validated changes from `develop` to `main`.

---

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]
```

Types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`

Examples:

```
feat(api): add nodes[] array to /api/status response
fix(monitor): handle None dns_latency in status response
test(coverage): add rate limit middleware edge case tests
docs(readme): remove hardcoded version from NOTE block
```

---

## Test Requirements

Before submitting a PR:

1. **All unit tests must pass:** `make test`
2. **Coverage must not drop below 60%** on `dashboard/monitor.py`
3. **New features require tests** — untested PRs will not be merged
4. **Tests must be Windows-compatible** (no `os.chmod` in tests without guards)

Test file conventions:

- File: `tests/test_<feature>.py`
- Class: `class Test<Feature>:`
- Method: `def test_<scenario>:`
- Use `@pytest.mark.asyncio` for async tests
- Use `@pytest.mark.integration` for tests requiring Docker

---

## PR Checklist

Before opening a pull request, confirm:

- [ ] Tests pass: `make test`
- [ ] No new linting errors: `make lint`
- [ ] `VERSION` file bumped (patch for fixes, minor for features)
- [ ] `CHANGELOG.md` updated with a concise entry under `[Unreleased]`
- [ ] PR targets the `develop` branch (never `main` directly)
- [ ] PR description explains _what_ changed and _why_

---

## Reporting Issues

Use [GitHub Issues](https://github.com/JBakers/pihole-sentinel/issues). Please include:

- Pi-hole version
- Sentinel version (`cat VERSION`)
- Relevant log output
- Steps to reproduce

For security vulnerabilities, see [SECURITY.md](SECURITY.md) — do **not** open a public issue.
