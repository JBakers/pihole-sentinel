# Branch Protection Rules Setup Guide

**Last Updated:** 2025-11-16
**Repository:** JBakers/pihole-sentinel

This guide explains how to configure GitHub branch protection rules to enforce the branching strategy.

---

## Overview

To maintain code quality and prevent accidental changes, we protect the following branches:

- **`main`** - Production releases only, strictly controlled
- **`testing`** - QA and integration testing, controlled
- **`develop`** - Active development, basic protection

### GitHub Plan and Repository Type Requirements

**Important:** Branch protection features depend on your GitHub plan AND repository type:

| Feature | Personal Repo (Free) | Personal Repo (Pro) | Organization Repo (Team/Enterprise) |
|---------|---------------------|---------------------|-------------------------------------|
| Require PR before merging | ✓ | ✓ | ✓ |
| Required approvals | ✗ (0 only) | ✓ (1+) | ✓ (1+) |
| **Restrict who can push** | ✗ | **✗** | **✓** |
| Require status checks | ✓ | ✓ | ✓ |
| CODEOWNERS | ✓ | ✓ | ✓ |
| Bypass list | ✗ | ✗ | ✓ |

**Key Limitation for Personal Repositories:**
- **Even with GitHub Pro**, you CANNOT restrict who can push to branches
- This feature ONLY works for Organization-owned repositories
- For personal repos, protection relies on "Require pull request before merging"

**For solo developers on personal repositories:**
- You can require PRs and approvals (with Pro)
- You can require status checks
- You CANNOT restrict push access (organization feature only)
- Protection relies on workflow discipline

---

## Setup Instructions

### Step 1: Access Branch Protection Settings

1. Go to your GitHub repository: `https://github.com/JBakers/pihole-sentinel`
2. Click on **Settings** (top menu)
3. Click on **Branches** (left sidebar)
4. Under "Branch protection rules", click **Add rule** or **Add branch protection rule**

---

## Protection Rules for `main`

### Rule Configuration

**Branch name pattern:** `main`

#### Settings to Enable:

1. **Require a pull request before merging** ✓
   - **Required approvals:** `1`
   - **Dismiss stale pull request approvals when new commits are pushed** ✓
   - **Require review from Code Owners** ✓ (if you have a CODEOWNERS file)
   - **Restrict who can dismiss pull request reviews**
     - Add: Your GitHub username (only you can dismiss reviews)

2. **Require status checks to pass before merging** ✓
   - **Require branches to be up to date before merging** ✓
   - Status checks to require (if you set up CI/CD):
     - `tests` (unit tests)
     - `integration-tests` (integration tests)
     - `lint` (code quality checks)

3. **Require conversation resolution before merging** ✓

4. **Require signed commits** ✓ (optional, but recommended for security)

5. **Require linear history** ✓ (prevents merge commits, keeps history clean)

6. **Include administrators** ✓ (even you must follow these rules)

7. **Restrict who can push to matching branches** **[ORGANIZATION REPOSITORIES ONLY]**
   - **Important:** This option only appears for Organization-owned repositories
   - **Personal repositories:** You will NOT see this option (even with GitHub Pro)
   - If you see this option (organization repo):
     - Enable "Restrict pushes that create matching branches"
     - Add specific users/teams who can push
     - Or leave empty to allow no direct pushes (force PR workflow)
   - If you DON'T see this option (personal repo):
     - **This is normal and expected**
     - Skip this setting entirely
     - Your protection relies on "Require PR before merging" (step 1)
     - You can still approve and merge your own PRs

8. **Allow force pushes** ✗ (disabled - prevent history rewriting)

9. **Allow deletions** ✗ (disabled - prevent accidental deletion)

10. **Require deployments to succeed before merging** (optional)

---

## Protection Rules for `testing`

### Rule Configuration

**Branch name pattern:** `testing`

#### Settings to Enable:

1. **Require a pull request before merging** ✓
   - **Required approvals:** `1`
   - **Dismiss stale pull request approvals when new commits are pushed** ✓
   - **Require review from Code Owners** ✓
   - **Restrict who can dismiss pull request reviews**
     - Add: Your GitHub username

2. **Require status checks to pass before merging** ✓
   - **Require branches to be up to date before merging** ✓
   - Status checks to require:
     - `tests` (unit tests)
     - `lint` (code quality)

3. **Require conversation resolution before merging** ✓

4. **Require signed commits** ✓ (optional)

5. **Include administrators** ✓

6. **Restrict who can push to matching branches** **[ORGANIZATION REPOSITORIES ONLY]**
   - Personal repos: You will NOT see this option - skip it
   - Organization repos: Add specific users/teams who can push

7. **Allow force pushes** ✗ (disabled)

8. **Allow deletions** ✗ (disabled)

---

## Protection Rules for `develop`

### Rule Configuration

**Branch name pattern:** `develop`

#### Settings to Enable:

1. **Require a pull request before merging** ✓ (optional, for stricter workflow)
   - **Required approvals:** `0` or `1` (your choice)
   - This ensures code review even for development

2. **Require status checks to pass before merging** ✓
   - **Require branches to be up to date before merging** ✓
   - Status checks to require:
     - `tests` (unit tests must pass)
     - `lint` (code quality checks)

3. **Include administrators** ✗ (you can push directly if needed)

4. **Allow force pushes** ✗ (disabled - protects against accidental history rewriting)

5. **Allow deletions** ✗ (disabled)

---

## Setting Up Code Owners (Optional but Recommended)

Create a file `.github/CODEOWNERS` in your repository:

```
# Default owner for everything
*       @YourGitHubUsername

# Specific paths (examples)
/dashboard/*        @YourGitHubUsername
/keepalived/*       @YourGitHubUsername
/setup.py           @YourGitHubUsername
*.md                @YourGitHubUsername
```

This automatically requests your review on all pull requests.

---

## Restricting Merge Access

### For Personal Repositories (like JBakers/pihole-sentinel)

**You CANNOT restrict who can push** even with GitHub Pro. Instead, use these protections:

1. **Require pull request before merging** (step 1 in protection rules)
   - This forces you to create a PR instead of pushing directly
   - You can approve and merge your own PRs

2. **Include administrators** (step 6 in protection rules)
   - Even as admin, you must follow the PR workflow
   - Prevents accidental direct pushes

3. **Repository access control:**
   - Go to **Settings** → **Collaborators**
   - Don't add any collaborators (if solo project)
   - If you have collaborators, give them "Read" access only

**Recommendation for Solo Developers:**
- Enable "Require PR before merging" with 1 required approval
- Enable "Include administrators"
- This creates a good workflow without needing organization features

### For Organization Repositories

If you transfer your repo to a GitHub Organization (Team/Enterprise plan):

1. Go to branch protection rule for `main`
2. Enable "Restrict who can push to matching branches"
3. Add only specific users/teams to the allowed list
4. Create a "Maintainers" team for better control
5. Repeat for `testing` branch

**To transfer to organization:**
1. Create a GitHub Organization (requires Team plan)
2. Go to repo **Settings** → **General**
3. Scroll to "Danger Zone"
4. Click "Transfer ownership"

---

## Workflow After Setup

### For Your Daily Work

```bash
# Create feature branch
git checkout develop
git checkout -b feature/my-feature

# Make changes, commit
git add .
git commit -m "feat: add feature"

# Push feature branch
git push -u origin feature/my-feature

# Create PR to develop (on GitHub)
# Review and merge (you can self-approve or set approvals to 0)
```

### Merging to Testing

```bash
# Create PR from develop to testing (on GitHub)
# You must approve the PR (if required approvals > 0)
# Merge after approval and status checks pass
```

### Merging to Main

```bash
# Create PR from testing to main (on GitHub)
# You must approve the PR
# All status checks must pass
# Merge after thorough testing
```

---

## Setting Up GitHub Actions (CI/CD)

To enable automatic status checks, create `.github/workflows/tests.yml`:

```yaml
name: Tests

on:
  push:
    branches: [ develop, testing, main ]
  pull_request:
    branches: [ develop, testing, main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r dashboard/requirements.txt
          pip install pylint flake8

      - name: Run linters
        run: |
          pylint dashboard/monitor.py || true
          flake8 dashboard/monitor.py || true

      - name: Run unit tests
        run: |
          # Add pytest when tests are implemented
          echo "Unit tests will run here"

      - name: Shell script check
        run: |
          sudo apt-get update
          sudo apt-get install -y shellcheck
          find . -name "*.sh" -exec shellcheck {} \; || true

  integration:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/testing' || github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3

      - name: Integration tests
        run: |
          # Add integration tests when implemented
          echo "Integration tests will run here"
```

This creates:
- A `tests` status check (runs on all branches)
- An `integration` status check (runs only on testing and main)

---

## Verifying Protection Rules

After setup, test the protection:

### Test 1: Try to Push Directly to Main

```bash
git checkout main
echo "test" >> README.md
git add README.md
git commit -m "test"
git push origin main
```

**Expected result:** Push should be rejected with:
```
! [remote rejected] main -> main (protected branch hook declined)
```

### Test 2: Try to Delete Protected Branch

```bash
git push origin --delete main
```

**Expected result:** Deletion should be rejected.

### Test 3: Create PR and Check Requirements

1. Create a PR from develop to testing
2. Verify you see:
   - "Review required" (if you enabled it)
   - "Status checks required" (if CI/CD is set up)
   - "Branch must be up-to-date" message

---

## Troubleshooting

### "Cannot merge due to required status checks"

- Ensure your CI/CD workflow is set up correctly
- Check the status checks section in branch protection rules
- Temporarily disable status checks if they're not yet implemented

### "Review required but I'm the only contributor"

- You can approve your own PR (GitHub allows this)
- Or set "Required approvals" to `0` for develop
- For main/testing, keep it at `1` for safety

### "I need to make an emergency fix"

- Create a hotfix branch from main
- Make the fix
- Create PR and approve it
- Or temporarily disable "Include administrators" setting

---

## Quick Configuration Guide

### For Personal Repositories (Most Common)

**Settings you WILL see and should enable:**
1. ✓ Require a pull request before merging (with 1 approval if you have Pro)
2. ✓ Require status checks to pass before merging
3. ✓ Require conversation resolution before merging
4. ✓ Require linear history
5. ✓ Include administrators
6. ✗ Allow force pushes (disabled)
7. ✗ Allow deletions (disabled)

**Settings you will NOT see (organization only):**
- ✗ Restrict who can push to matching branches
- ✗ Bypass list

**This is completely normal!** Your protection still works through the PR requirement.

### For Organization Repositories

All of the above, PLUS:
- ✓ Restrict who can push to matching branches
- ✓ Bypass list (for CI/CD or specific users)

---

## Summary Checklist

After following this guide, you should have:

**Essential (All Repository Types):**
- [ ] Branch protection rule for `main` configured
- [ ] Branch protection rule for `testing` configured
- [ ] Branch protection rule for `develop` configured
- [ ] "Require pull request before merging" enabled on `main` and `testing`
- [ ] "Include administrators" enabled (forces you to use PRs)
- [ ] Force pushes disabled on all protected branches
- [ ] Branch deletions disabled on all protected branches

**If You Have GitHub Pro (Personal Repo):**
- [ ] Required approvals set to 1 (you can approve your own PRs)

**If You Have Organization Repository:**
- [ ] "Restrict who can push to matching branches" configured
- [ ] Only specific users/teams can merge to `main` and `testing`

**Optional (All Repository Types):**
- [ ] CODEOWNERS file created (if applicable)
- [ ] GitHub Actions CI/CD set up
- [ ] Status checks configured and required
- [ ] Tested protection rules work correctly

---

## Reference Links

- [GitHub Branch Protection Rules Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub Code Owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitHub Actions](https://docs.github.com/en/actions)

---

**Questions?** Open a GitHub issue or discussion.

**Last Updated:** 2025-11-16
