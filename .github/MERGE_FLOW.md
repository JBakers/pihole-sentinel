# Git Merge Flow

```
feature/* / fix/* ──► develop ──► testing ──► main
```

**Allowed:** feature → develop → testing → main (one direction only, via PR)

**Blocked:** Any reverse merge (testing→develop, main→testing, main→develop)

**Hotfixes:** Branch from main, merge back to main AND cherry-pick to develop/testing.

**Enforcement:** `.githooks/pre-merge-commit` blocks reverse merges.

See [CLAUDE.md](../CLAUDE.md) for full branch rules.
