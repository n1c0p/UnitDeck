# Changelog

**English** | [Italiano](CHANGELOG.it.md)

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- System services tab: same features as the user tab on the system bus; privileged actions use D-Bus interactive authorization, so polkit shows the desktop's authentication dialog only when needed, and a cancelled or refused authentication is reported in the status bar without any crash.
- User services tab: searchable and filterable table of the session's `.service` units (including installed but not loaded ones), start/stop/restart/reload, enable/disable at boot, mask/unmask, journal viewer with live follow and priority filter, live updates from systemd's D-Bus signals, context menu and keyboard shortcuts.
- Interface in English and Italian: follows the desktop language, selectable from the Settings menu.
- Menu bar with Settings and Info menus, About dialogs, and an update mechanism: check against GitHub Releases (at startup, optional, and on demand), download of the `.deb` with SHA256 verification, installation through `pkexec apt-get`.
- Project skeleton: `pyproject.toml` with `setuptools-scm` versioning, `unitdeck` package runnable with `python -m unitdeck`, refusing to start as root.
- REUSE compliance: `LICENSES/`, `REUSE.toml` and SPDX headers in every source file.
- `CONTRIBUTING.md` and `CONTRIBUTING.it.md` with branch model, release process and GitHub rulesets.
- GitHub Actions workflows: `ci` (ruff, `reuse lint`, pytest) and the `branch-origin` and `release-check` gates for pull requests into `main`.
- Project README, in English and Italian.
- GPL-3.0-or-later license.
- This changelog, in English and Italian.

[Unreleased]: https://github.com/n1c0p/UnitDeck/commits/develop
