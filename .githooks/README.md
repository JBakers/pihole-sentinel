# Git Hooks

This directory contains git hooks to enforce code quality and versioning standards.

## Available Hooks

### pre-commit

Enforces version management rules before every commit:

- ✅ Ensures `VERSION` file is updated for code changes
- ✅ Ensures `CHANGELOG.md` is updated for code changes
- ✅ Checks for `print()` statements in Python files (except setup.py)
- ✅ Checks for CRLF line endings in bash scripts
- ✅ Allows documentation-only changes without version updates

### pre-merge-commit

🚫 **CRITICAL SECURITY HOOK** - Prevents AI agents from merging to protected branches:

- ✅ Blocks all merges to `testing` branch (only user may merge)
- ✅ Blocks all merges to `main` branch (only user may merge)
- ✅ Enforces CLAUDE.md mandatory rules for AI agents
- ✅ Provides clear error messages and instructions
- ✅ Allows repository owner to override with `--no-verify` if needed

**Why this hook exists:**
This hook prevents AI assistants (Claude, Copilot, etc.) from accidentally merging to protected branches. According to CLAUDE.md project rules, ONLY the repository owner may merge from `develop` → `testing` → `main`.

## Installation

### Option 1: Copy to .git/hooks (Recommended)

```bash
# Install both hooks
cp .githooks/pre-commit .git/hooks/pre-commit
cp .githooks/pre-merge-commit .git/hooks/pre-merge-commit
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-merge-commit
```

### Option 2: Configure Git to use .githooks directory (Easiest)

```bash
git config core.hooksPath .githooks
```

This applies **all hooks** in `.githooks/` directory automatically (both pre-commit and pre-merge-commit).

### Quick Install Script

```bash
# One-liner to install both hooks using Option 2
git config core.hooksPath .githooks && echo "✓ Git hooks installed successfully!"
```

## Testing the Hooks

### Testing pre-commit hook

After installation, try making a code change without updating VERSION:

```bash
# Make a change to a Python file
echo "# test comment" >> dashboard/monitor.py

# Stage the change
git add dashboard/monitor.py

# Try to commit (should fail)
git commit -m "test: trying to commit without version update"

# You should see:
# ✗ ERROR: VERSION file not updated!
# ✗ ERROR: CHANGELOG.md not updated!
```

### Testing pre-merge-commit hook

Test the merge protection (should block merges to testing/main):

```bash
# Switch to testing branch
git checkout testing

# Try to merge develop (should fail)
git merge develop

# You should see:
# 🚫 MERGE GEBLOKKEERD: Beschermde Branch
# ❌ FOUT: Kan niet mergen naar 'testing' branch
```

**Expected behavior:**
- ✅ Merge to `testing` or `main` is **blocked** with clear error message
- ✅ Hook explains why (CLAUDE.md rules)
- ✅ Hook provides override instructions for repository owner
- ✅ Hook tells AI agents to abort the merge

## Bypassing the Hooks

**NOT RECOMMENDED** - Only use in exceptional circumstances:

### Bypass pre-commit hook

```bash
git commit --no-verify -m "your commit message"
```

### Bypass pre-merge-commit hook

```bash
# During merge
git merge develop --no-verify

# Or if merge is already in progress
git merge --continue --no-verify
```

**⚠️ WARNING:** Bypassing hooks should only be done by the repository owner and only when absolutely necessary.

## Uninstalling

### If using Option 1:

```bash
# Remove individual hooks
rm .git/hooks/pre-commit
rm .git/hooks/pre-merge-commit

# Or remove all hooks
rm .git/hooks/pre-*
```

### If using Option 2:

```bash
git config --unset core.hooksPath
```

## Customization

To customize the hook behavior:

1. Edit the hook file: `.githooks/pre-commit` or `.githooks/pre-merge-commit`
2. If using Option 1, reinstall: `cp .githooks/[hook-name] .git/hooks/[hook-name]`
3. If using Option 2, changes are applied automatically (hooks are symlinked)

## Security Notes

- The `pre-merge-commit` hook is a **critical security measure** for AI-assisted development
- DO NOT remove or disable this hook if working with AI assistants
- This hook prevents costly mistakes (accidental merges to production branches)
- Repository owner can always override with `--no-verify` when needed
