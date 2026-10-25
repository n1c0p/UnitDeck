<!--
SPDX-License-Identifier: GPL-3.0-or-later
SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
-->
## What and why



## Checklist

- [ ] Branch created from `develop`, target `develop` (releases: `develop` → `main`, see CONTRIBUTING)
- [ ] Commit messages follow Conventional Commits
- [ ] `ruff check . && ruff format --check .`, `reuse lint` and `pytest` pass
- [ ] Changes to `README`, `CHANGELOG` or `CONTRIBUTING` are mirrored in the other language
- [ ] `CHANGELOG.md` and `CHANGELOG.it.md` updated under Unreleased
- [ ] No real system service was touched while testing; throwaway units are named `test-unitdeck-*`
