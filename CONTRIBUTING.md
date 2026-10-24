# Contributing to UnitDeck

**English** | [Italiano](CONTRIBUTING.it.md)

Thank you for considering a contribution. This document describes how the repository is organised and how changes get in.

## Branches

| Branch | Purpose |
|--------|---------|
| `main` | Always matches the latest release. Only release PRs from `develop` and `hotfix/*` branches land here. |
| `develop` | Ongoing development, default branch, target of all feature and fix PRs. |
| `feature/*`, `fix/*` | Created from `develop`, merged back into `develop` with a **squash** merge. |
| `hotfix/*` | Urgent fixes created from `main`, merged into `main` with a merge commit and then brought back into `develop`. |

## Development setup

```bash
git clone https://github.com/n1c0p/UnitDeck.git
cd UnitDeck
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m unitdeck
```

Before every commit run the same checks as the CI:

```bash
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/reuse lint
.venv/bin/pytest
```

While developing, never touch real system services: use throwaway **user** units named `test-unitdeck-*.service` and remove them when you are done.

## Pull request flow

1. Start from an up-to-date `develop` in a `feature/<topic>` or `fix/<topic>` branch.
2. Use [Conventional Commits](https://www.conventionalcommits.org/) messages: `feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `refactor:`, `test:`.
3. Every source file (Python, scripts, workflows, `.policy`, `.desktop`, templates) starts with the SPDX header:

   ```python
   # SPDX-License-Identifier: GPL-3.0-or-later
   # SPDX-FileCopyrightText: 2026 Nicola (n1c0p)
   ```

   Files that cannot carry a header are listed in `REUSE.toml`. `reuse lint` must pass.
4. Add an entry to the **Unreleased** section of `CHANGELOG.md` **and** `CHANGELOG.it.md` for every completed feature or fix.
5. Do not commit personal or network data: no IP addresses, usernames, hostnames or local paths, not even in tests or examples.
6. Open the PR against `develop`. The `ci` check (ruff, `reuse lint`, pytest) must pass. PRs are squash-merged.

## Bilingual documentation

`README`, `CHANGELOG` and `CONTRIBUTING` exist in English (`*.md`, the reference version) and Italian (`*.it.md`), each with a language switcher at the top. Any change to one language must be mirrored in the other **in the same commit**. Interface strings are written in English in the code, wrapped in `tr()`, and translated in the Italian catalogue in `src/unitdeck/i18n.py`; a test fails when a string is missing from the catalogue. If you are not comfortable with Italian, say so in the PR and the maintainer will translate.

## Versioning

Versions follow [Semantic Versioning](https://semver.org/). The installed version comes **only** from git tags `vX.Y.Z` through `setuptools-scm`: never write a version number by hand in code. The first releases are `0.x`.

## Preparing a release

1. Open a PR from `develop` to `main`.
2. In that PR, rename the `## [Unreleased]` section of **both** `CHANGELOG.md` and `CHANGELOG.it.md` to `## [X.Y.Z] - YYYY-MM-DD`, with the same version and date in both files, and add a fresh empty `## [Unreleased]` section above it.
3. The `release-check` job fails if the version is missing or invalid, if the tag `vX.Y.Z` already exists, if the version is not greater than the latest release, or if the Italian changelog does not contain the same version and date. The `branch-origin` job fails if the PR does not come from `develop` or a `hotfix/*` branch.
4. Merge with a **merge commit** (not squash). The `release.yml` workflow then tags the merge commit, builds the `.deb`, publishes the GitHub Release with the changelog section as notes, and opens a PR `main` → `develop` titled `chore: sync main into develop after vX.Y.Z`.
5. Merge the sync PR into `develop` with a merge commit.

If the release workflow fails, fix the cause and re-run it manually from the Actions tab (`workflow_dispatch`): it is idempotent and exits cleanly when the tag already exists.

### Hotfixes

Create `hotfix/<topic>` from `main`, open a PR to `main` following the release steps above (the changelog gets a new patch version), then open a second PR to bring the fix into `develop`.

## GitHub rulesets

The repository relies on these rulesets (Settings → Rules → Rulesets). Required status checks can only be selected after the workflow has run at least once.

| Target | Rules |
|--------|-------|
| Branch `main` | Restrict deletions; block force pushes; require a pull request (0 approvals); required checks `ci`, `branch-origin`, `release-check`; **no** linear history requirement. |
| Branch `develop` | Restrict deletions; block force pushes; require a pull request (0 approvals); required check `ci`. |
| Tags `v*` | Restrict updates and deletions (creation stays allowed, the release workflow creates them). |
