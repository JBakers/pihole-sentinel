# Git Merge Flow

```
feature/* / fix/* ---> develop ---> main
```

**Allowed:** feature branches merge into `develop`. The repository owner promotes
`develop` to `main` through a pull request after release validation.

**Blocked:** reverse merges from `main` to `develop`, and merges from `develop`
back into feature branches.

**Hotfixes:** branch from `main`, merge the fix into `develop`, validate it, and let
the repository owner promote `develop` to `main`.

**Enforcement:** `.github/workflows/enforce-merge-direction.yml` validates pull
request direction. `.githooks/pre-merge-commit` prevents agents from merging into
`main`.

See [CLAUDE.md](../CLAUDE.md) for full branch rules.
