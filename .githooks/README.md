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

## Installation

### Option 1: Copy to .git/hooks (Recommended)

```bash
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### Option 2: Configure Git to use .githooks directory

```bash
git config core.hooksPath .githooks
```

This applies all hooks in `.githooks/` directory automatically.

## Testing the Hook

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

## Bypassing the Hook

**NOT RECOMMENDED** - Only use in exceptional circumstances:

```bash
git commit --no-verify -m "your commit message"
```

## Uninstalling

### If using Option 1:

```bash
rm .git/hooks/pre-commit
```

### If using Option 2:

```bash
git config --unset core.hooksPath
```

## Customization

To customize the hook behavior, edit `.githooks/pre-commit` and then reinstall using the instructions above.
