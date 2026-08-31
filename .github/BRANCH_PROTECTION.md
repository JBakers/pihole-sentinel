# Branch Protection

Pi-hole Sentinel uses two permanent branches:

- `develop`: active development and integration.
- `main`: stable production releases.

Feature and fix branches target `develop`. Only the repository owner promotes a
validated `develop` revision to `main` through a pull request.

## Main Protection Rule

Configure a GitHub ruleset or branch protection rule for `main` with:

- Require a pull request before merging.
- Require the `Code Quality` status checks to pass.
- Require branches to be up to date before merging.
- Block force pushes and branch deletion.
- Apply the rule to administrators when practical.
- Keep the GitHub default branch set to `main`.

Only the repository owner may approve and merge the release pull request from
`develop` to `main`.

## Develop Settings

`develop` is the active integration branch. Recommended settings:

- Run code-quality checks on pushes and pull requests.
- Block force pushes and branch deletion.
- Target `develop` from short-lived feature, fix, chore, and documentation
  branches.
- Delete short-lived branches after merge.

Direct work by repository agents is restricted to `develop` by `CLAUDE.md`.

## Allowed Flow

```text
feature/*, fix/*, chore/*, docs/* -> develop -> main
```

The `enforce-merge-direction.yml` workflow blocks reverse pull requests from
`main` to `develop` and from `develop` back into short-lived branches.

## Release Procedure

1. Complete the release readiness checklist in `PLAN.md` on `develop`.
2. Confirm `make test`, `make lint`, and relevant integration tests pass.
3. Open a pull request from `develop` to `main`.
4. Review the diff, release notes, version, and artifacts.
5. Let the repository owner merge the pull request.
6. Create a consistent annotated `vX.Y.Z` release tag.

## Local Safeguards

Install the repository hooks with:

```bash
git config core.hooksPath .githooks
```

The pre-merge hook prevents agents from merging into `main`. The repository
owner can deliberately override it with `--no-verify` after completing release
validation.
