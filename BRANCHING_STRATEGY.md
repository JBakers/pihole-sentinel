# Branching Strategy - Pi-hole Sentinel

**Last Updated:** 2025-11-16
**Version:** 1.0

This document outlines the Git branching strategy for Pi-hole Sentinel development.

---

## Overview

Pi-hole Sentinel uses a **three-tier branching strategy** to ensure code quality and stability:

```
develop (active development)
   ↓
testing (QA and integration testing)
   ↓
main (stable production releases)
```

---

## Branch Descriptions

### `main` - Production Branch

**Purpose:** Stable, production-ready releases only

**Characteristics:**
- Contains only tested, stable code
- Each commit should be tagged with a version number
- Only accepts merges from `testing` branch
- Protected branch (no direct commits)
- Represents what end-users should deploy

**Merge Criteria:**
- All tests pass on `testing`
- At least 7 days of stable operation
- Security audit completed
- Documentation up-to-date
- Sign-off from maintainer

**Deployment:**
Users should always deploy from `main` for production environments.

---

### `testing` - QA Branch

**Purpose:** Integration testing and quality assurance

**Characteristics:**
- Code ready for testing but not yet production-ready
- Full integration test suite runs here
- Performance and stress testing
- Security testing
- Browser compatibility testing
- Only accepts merges from `develop`
- Protected branch (no direct commits)

**Merge Criteria from `develop`:**
- All unit tests pass
- Code review completed
- CHANGELOG.md updated
- No known critical bugs

**Merge Criteria to `main`:**
- All integration tests pass (see `.github/TESTING_TODO.md`)
- No critical or high-severity bugs
- At least 7 days of stable operation
- Documentation verified
- Sign-off from maintainer

**Bug Fixes:**
If bugs are found during testing:
1. Fix the bug in `develop`
2. Merge `develop` → `testing`
3. Re-test to verify fix

---

### `develop` - Development Branch

**Purpose:** Active development and feature integration

**Characteristics:**
- Default branch for new development
- Feature branches merge here first
- May contain unstable code
- Continuous integration runs here
- Unit tests must pass before merge

**What Gets Merged Here:**
- Feature branches
- Bug fix branches
- Documentation updates
- Dependency updates

**Workflow:**
1. Create feature branch from `develop`
2. Develop feature
3. Test locally
4. Create pull request to `develop`
5. Code review
6. Merge to `develop`

---

## Feature Branch Workflow

### Creating a Feature Branch

```bash
# Ensure develop is up-to-date
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

### Working on a Feature

```bash
# Make changes
git add .
git commit -m "feat: add new feature"

# Push to remote
git push -u origin feature/your-feature-name
```

### Merging Back to Develop

```bash
# Ensure your branch is up-to-date
git checkout feature/your-feature-name
git fetch origin
git merge origin/develop

# Resolve any conflicts
# Run tests
# Push changes

# Create pull request on GitHub
# Request code review
# Merge to develop after approval
```

---

## Release Workflow

### Preparing a Release

1. **Development Phase** (`develop`)
   ```bash
   # Work on features in develop
   git checkout develop
   # Develop, test, commit
   ```

2. **Testing Phase** (`testing`)
   ```bash
   # Merge to testing when ready
   git checkout testing
   git merge develop
   git push origin testing

   # Run all integration tests (see .github/TESTING_TODO.md)
   # Monitor for at least 7 days
   # Document test results
   ```

3. **Production Release** (`main`)
   ```bash
   # After all tests pass
   git checkout main
   git merge testing

   # Update VERSION file
   echo "0.9.0" > VERSION
   git add VERSION
   git commit -m "chore: bump version to 0.9.0"

   # Create tag
   git tag -a v0.9.0 -m "Release version 0.9.0"

   # Push changes
   git push origin main
   git push origin v0.9.0
   ```

4. **Post-Release**
   ```bash
   # Merge main back to develop and testing
   git checkout develop
   git merge main
   git push origin develop

   git checkout testing
   git merge main
   git push origin testing
   ```

---

## Hotfix Workflow

For critical bugs in production:

```bash
# Create hotfix branch from main
git checkout main
git checkout -b hotfix/critical-bug-fix

# Fix the bug
git add .
git commit -m "fix: critical security vulnerability"

# Merge to main
git checkout main
git merge hotfix/critical-bug-fix

# Tag immediately
git tag -a v0.8.1 -m "Hotfix: security vulnerability"

# Push
git push origin main
git push origin v0.8.1

# Merge back to testing and develop
git checkout testing
git merge main
git push origin testing

git checkout develop
git merge main
git push origin develop

# Delete hotfix branch
git branch -d hotfix/critical-bug-fix
git push origin --delete hotfix/critical-bug-fix
```

---

## Branch Naming Conventions

### Feature Branches
- `feature/descriptive-name` - New features
- `feat/descriptive-name` - Alternative for features

### Bug Fix Branches
- `fix/issue-description` - Bug fixes
- `bugfix/issue-description` - Alternative for bug fixes

### Documentation Branches
- `docs/what-is-being-documented` - Documentation updates

### Refactoring Branches
- `refactor/what-is-being-refactored` - Code refactoring

### Examples
- `feature/email-notifications`
- `fix/vip-detection-retry-logic`
- `docs/update-installation-guide`
- `refactor/split-monitor-modules`

---

## Commit Message Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type: brief description (50 chars max)

Longer explanation if needed (72 chars per line).

Fixes #123
```

### Types
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, no logic change)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks (dependencies, build config)
- `perf:` - Performance improvements
- `ci:` - CI/CD changes
- `security:` - Security improvements

### Examples
```
feat: add HTTPS support to monitor dashboard

fix: retry VIP detection on ARP table population failure

docs: update CLAUDE.md with new branching strategy

chore: bump FastAPI to 0.110.0

security: sanitize user input in notification settings
```

---

## Protected Branches

The following branches should be protected on GitHub:

### `main`
- Require pull request reviews (1 approver)
- Require status checks to pass
- Require branches to be up to date
- No force pushes
- No deletions

### `testing`
- Require pull request reviews (1 approver)
- Require status checks to pass
- Require branches to be up to date
- No force pushes
- No deletions

### `develop`
- Require status checks to pass
- No force pushes
- No deletions

---

## Version Numbering

Pi-hole Sentinel follows [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH
```

- **MAJOR** - Breaking changes, incompatible API changes
- **MINOR** - New features, backward-compatible
- **PATCH** - Bug fixes, backward-compatible

### Examples
- `0.8.0` → `0.9.0` - New feature (email notifications)
- `0.9.0` → `0.9.1` - Bug fix (VIP detection issue)
- `0.9.1` → `1.0.0` - Breaking change (new Pi-hole API version)

### Pre-release Versions
- `1.0.0-alpha.1` - Alpha release
- `1.0.0-beta.1` - Beta release
- `1.0.0-rc.1` - Release candidate

---

## Continuous Integration

### Automated Tests

**On Push to `develop`:**
- Run unit tests
- Run linters (pylint, shellcheck)
- Check code formatting
- Security scan

**On Push to `testing`:**
- All tests from `develop`
- Integration tests
- Performance tests
- Security audit

**On Push to `main`:**
- All tests from `testing`
- Create GitHub release
- Update documentation site

---

## Quick Reference

### Daily Development
```bash
git checkout develop
git pull origin develop
git checkout -b feature/my-feature
# ... make changes ...
git add .
git commit -m "feat: add awesome feature"
git push -u origin feature/my-feature
# Create PR to develop
```

### Merging to Testing
```bash
git checkout testing
git pull origin testing
git merge develop
git push origin testing
# Run integration tests
```

### Creating a Release
```bash
git checkout main
git pull origin main
git merge testing
echo "0.9.0" > VERSION
git add VERSION
git commit -m "chore: bump version to 0.9.0"
git tag -a v0.9.0 -m "Release version 0.9.0"
git push origin main --tags
```

---

## Resources

- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)

---

## Todo Lists

- **Develop Branch:** See `.github/DEVELOP_TODO.md`
- **Testing Branch:** See `.github/TESTING_TODO.md`

---

**Questions?** Open a GitHub issue or discussion.

**Last Updated:** 2025-11-16
