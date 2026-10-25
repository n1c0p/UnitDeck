# Changelog

**English** | [Italiano](CHANGELOG.it.md)

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.2] - 2026-10-25

### Fixed

- Update download crashed the application as soon as it started (incompatible progress signal); unhandled errors now show a dialog instead of terminating UnitDeck.

## [0.1.1] - 2026-10-25

### Fixed

- SMB mount template: start is idempotent when the share is already mounted, stop unmounts the location gvfs really registered and no longer leaves the unit failed.

### Added

- Code of conduct (Contributor Covenant 2.1), security policy, issue and pull request templates.

### Changed

- CI runs on every pull request, documentation-only and empty diffs included, so the required `ci` check always reports.

## [0.1.0] - 2026-10-24

### Added

- Debian package: PyInstaller one-directory bundle in `/opt/unitdeck` with `/usr/bin/unitdeck`, helper in `/usr/libexec/unitdeck`, polkit policy, desktop file, icon and man page; built by `packaging/build-deb.sh`, checked with `lintian` and a clean-install test. `unitdeck --version` and `unitdeck --check`.
- CI: preview package on every push to `develop` (artifact, 14 days); `release.yml` tags the merge into `main`, builds the package, publishes the GitHub Release with the SHA256 checksum and the changelog section as notes, and opens the sync PR `main` → `develop`.
- New service wizard: name and template, guided fields (with `User=`/`Group=` and root warning for system services, `WantedBy` prefilled per scope), editable preview checked with `systemd-analyze verify`, enable/start options; the new unit is selected in the table. Templates are files in `src/unitdeck/templates/`: empty, one-shot, long-running, SMB mount with gio (user only).
- Linger switch in the user tab, through logind's `SetUserLinger` with interactive authorization.
- Delete now stops and disables the unit before removing its files; editor colours adapt to dark themes; window size and position are remembered.
- Service editor: syntax-highlighted editor with line numbers next to the effective configuration; drop-in `override.conf` for package units (full copy as an option), direct edit for user-created units; `systemd-analyze verify` before saving, `.bak` backup, automatic `daemon-reload` and restart prompt. "Restore original" (`RevertUnitFiles`) and "Delete" for user-created units.
- Privileged helper `unitdeck-helper` (standard library only) with its polkit policy `eu.nicop.unitdeck.manage-unit-files` (`auth_admin_keep`): writes drop-ins and units only under `/etc/systemd/system`, with strict name and path validation.
- System services tab: same features as the user tab on the system bus; privileged actions use D-Bus interactive authorization, so polkit shows the desktop's authentication dialog only when needed, and a cancelled or refused authentication is reported in the status bar without any crash.
- "Reset failed state" action and, when a job fails, systemd's own result (e.g. `start-limit-hit`) in the error message.
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

[Unreleased]: https://github.com/n1c0p/UnitDeck/compare/v0.1.2...develop
[0.1.2]: https://github.com/n1c0p/UnitDeck/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/n1c0p/UnitDeck/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/n1c0p/UnitDeck/releases/tag/v0.1.0
