# Git Merge Flow - Visual Guide

**Last Updated:** 2025-11-17

This document provides a visual representation of the allowed and blocked merge flows in the pihole-sentinel repository.

---

## ✅ Allowed Merge Flow

```
┌─────────────┐
│   Feature   │
│  Branches   │
│             │
│ feature/*   │
│   fix/*     │
│  chore/*    │
│   docs/*    │
└──────┬──────┘
       │
       │ ✅ ALLOWED
       │ (via PR)
       ▼
┌─────────────┐
│   develop   │◄─── Integration & development
│             │     testing happens here
└──────┬──────┘
       │
       │ ✅ ALLOWED
       │ (via PR)
       ▼
┌─────────────┐
│   testing   │◄─── QA validation &
│             │     comprehensive testing
└──────┬──────┘
       │
       │ ✅ ALLOWED
       │ (via PR)
       ▼
┌─────────────┐
│    main     │◄─── Production releases
│             │     only
└─────────────┘
```

---

## ❌ Blocked Merge Flows

### 1. Testing → Develop (BLOCKED)

```
┌─────────────┐
│   develop   │
└──────▲──────┘
       │
       │ ❌ BLOCKED!
       │ Wrong direction
       │
┌──────┴──────┐
│   testing   │
└─────────────┘
```

**Why blocked:** Testing should flow TO main, not back to develop. If you need changes from testing in develop, cherry-pick specific commits or create a new feature branch.

---

### 2. Main → Testing (BLOCKED)

```
┌─────────────┐
│   testing   │
└──────▲──────┘
       │
       │ ❌ BLOCKED!
       │ Wrong direction
       │
┌──────┴──────┐
│    main     │
└─────────────┘
```

**Why blocked:** Main is the final destination, not the source. Hotfixes should branch from main, be fixed, then merge back to main AND be cherry-picked to develop/testing.

---

### 3. Main → Develop (BLOCKED)

```
┌─────────────┐
│   develop   │
└──────▲──────┘
       │
       │ ❌ BLOCKED!
       │ Wrong direction
       │
┌──────┴──────┐
│    main     │
└─────────────┘
```

**Why blocked:** Develop feeds into main, not the other way around. For hotfixes, use cherry-pick or create a feature branch.

---

## 🔥 Hotfix Workflow (Special Case)

When you need to fix a critical bug in production:

```
┌─────────────┐
│    main     │
└──────┬──────┘
       │
       │ 1. Create hotfix branch
       ▼
┌─────────────┐
│ hotfix/bug  │
└──────┬──────┘
       │
       │ 2. Fix the bug
       │ 3. Test thoroughly
       │
       ├─────────────┐
       │             │
       │             │ 4. Merge to main
       │             ▼
       │      ┌─────────────┐
       │      │    main     │
       │      └─────────────┘
       │
       │ 5. Cherry-pick to develop
       ▼
┌─────────────┐
│   develop   │
└──────┬──────┘
       │
       │ 6. Cherry-pick to testing
       ▼
┌─────────────┐
│   testing   │
└─────────────┘
```

**Commands:**

```bash
# 1. Create hotfix from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug

# 2. Fix and commit
git add .
git commit -m "fix: critical bug in production"

# 3. Push and create PR to main
git push -u origin hotfix/critical-bug
# Create PR: hotfix/critical-bug → main

# 4. After merge to main, cherry-pick to develop
git checkout develop
git pull origin develop
git cherry-pick <commit-hash>
git push origin develop

# 5. Cherry-pick to testing
git checkout testing
git pull origin testing
git cherry-pick <commit-hash>
git push origin testing
```

---

## 🔄 Feature Development Workflow

### Standard Feature Flow

```
1. Branch from develop
   develop → feature/new-feature

2. Develop and test locally
   (commits to feature branch)

3. Create PR to develop
   feature/new-feature → develop

4. Code review & merge
   (feature merged into develop)

5. Merge develop to testing
   develop → testing (via PR)

6. QA testing in testing branch
   (comprehensive tests)

7. Merge testing to main
   testing → main (via PR)

8. Tag release in main
   git tag v1.0.0
```

### Example Commands

```bash
# 1. Create feature branch
git checkout develop
git pull origin develop
git checkout -b feature/amazing-feature

# 2. Make changes
git add .
git commit -m "feat: add amazing feature"

# 3. Push and create PR
git push -u origin feature/amazing-feature
# On GitHub: Create PR feature/amazing-feature → develop

# 4. After PR approved and merged, update develop
git checkout develop
git pull origin develop

# 5. Merge to testing (via PR on GitHub)
# On GitHub: Create PR develop → testing

# 6. After testing passes, merge to main (via PR)
# On GitHub: Create PR testing → main

# 7. Tag the release
git checkout main
git pull origin main
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

---

## 🛡️ How Enforcement Works

### GitHub Actions Workflow

The `.github/workflows/enforce-merge-direction.yml` workflow:

1. **Triggers** on every pull request
2. **Checks** the base and head branches
3. **Validates** against allowed patterns
4. **Fails** if direction is wrong
5. **Comments** on the PR with explanation

### Required Status Check

To make this mandatory:

1. Go to **Settings** → **Branches**
2. Edit branch protection for `develop`, `testing`, `main`
3. Enable **"Require status checks to pass before merging"**
4. Add **"check-merge-direction"** to required checks
5. Enable **"Require branches to be up to date before merging"**

Now PRs in the wrong direction **cannot** be merged even if you want to!

---

## 📋 Quick Reference

| Source Branch | Target Branch | Status | Notes |
|--------------|---------------|--------|-------|
| `feature/*` | `develop` | ✅ ALLOWED | Standard development workflow |
| `develop` | `testing` | ✅ ALLOWED | Deploy to testing for QA |
| `testing` | `main` | ✅ ALLOWED | Production release |
| `hotfix/*` | `main` | ✅ ALLOWED | Emergency production fixes |
| `hotfix/*` | `develop` | ✅ ALLOWED | Backport hotfix to develop |
| `testing` | `develop` | ❌ BLOCKED | Wrong direction! |
| `main` | `testing` | ❌ BLOCKED | Wrong direction! |
| `main` | `develop` | ❌ BLOCKED | Wrong direction! |
| `develop` | `feature/*` | ❌ BLOCKED | Features branch FROM develop |
| `testing` | `feature/*` | ❌ BLOCKED | Wrong direction! |

---

## ❓ FAQ

### Q: I accidentally created a PR in the wrong direction. What do I do?

**A:** Close the PR and create a new one in the correct direction. The GitHub Actions check will guide you.

### Q: I need to backport a fix from testing to develop. How?

**A:** Use `git cherry-pick` instead of merge:

```bash
git checkout develop
git cherry-pick <commit-hash-from-testing>
git push origin develop
```

### Q: What if I really need to merge backwards for an emergency?

**A:**
1. Document the reason clearly
2. Temporarily disable the "Require status checks" in branch protection
3. Merge your PR
4. Re-enable the status check immediately
5. Create an issue to track the technical debt

### Q: Can I bypass this as an admin?

**A:** Yes, but DON'T. The workflow exists to prevent mistakes. If you need to bypass:
1. Settings → Branches → Edit rule
2. Uncheck "Require status checks to pass"
3. Merge
4. Re-enable immediately

---

**Last Updated:** 2025-11-17
**Maintained by:** JBakers
