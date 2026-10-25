# UnitDeck

**English** | [Italiano](https://github.com/n1c0p/UnitDeck/blob/main/README.it.md)

[![License: GPL v3+](https://img.shields.io/badge/License-GPLv3%2B-blue.svg)](https://github.com/n1c0p/UnitDeck/blob/main/LICENSE)
[![Latest release](https://img.shields.io/github/v/release/n1c0p/UnitDeck?include_prereleases&sort=semver)](https://github.com/n1c0p/UnitDeck/releases)
[![Downloads](https://img.shields.io/github/downloads/n1c0p/UnitDeck/total?color=success)](https://github.com/n1c0p/UnitDeck/releases)
[![CI](https://github.com/n1c0p/UnitDeck/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/n1c0p/UnitDeck/actions/workflows/ci.yml)
[![REUSE status](https://api.reuse.software/badge/github.com/n1c0p/UnitDeck)](https://api.reuse.software/info/github.com/n1c0p/UnitDeck)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white)](https://www.riverbankcomputing.com/software/pyqt/)
[![Linux · systemd](https://img.shields.io/badge/Platform-Linux%20%C2%B7%20systemd-FCC624?logo=linux&logoColor=black)](https://systemd.io/)

**UnitDeck** is a desktop application for Linux to manage **systemd services**, both **system-wide** and **per-user**, from a clean graphical interface.

![UnitDeck main window: the system services tab](https://raw.githubusercontent.com/n1c0p/UnitDeck/main/docs/screenshot.png)

> **Status: early releases (0.x).** The first version is out and usable; expect rough edges and report them in the [issues](https://github.com/n1c0p/UnitDeck/issues).

## Why UnitDeck

Managing services usually means juggling `systemctl`, `systemctl --user`, `journalctl` and an editor opened with `sudo`. UnitDeck brings all of it into a single window, without ever running the interface as root.

## Features

- **Two tabs:** system services and user services, each in a searchable, filterable table showing load state, active state and boot status.
- **Quick actions on every row:** start, stop, restart, edit, plus reload, enable/disable at boot, logs, mask/unmask, restore original and delete.
- **Safe editing with drop-ins:** for services shipped by packages, changes are saved as `override.conf` drop-ins (like `systemctl edit`), so they survive package upgrades. A "Restore original" action reverts them. Every change is validated with `systemd-analyze verify` before saving.
- **New service wizard:** create system or user services from templates, with validation and an optional "enable and start now".
- **Live logs:** journal output for the selected service, with live follow and priority filter.
- **Live status:** updates come straight from systemd over D-Bus, no polling.
- **User lingering toggle:** let user services run without a graphical login.

## Security model

UnitDeck is designed to **never run as root**, and refuses to start if launched with root privileges.

- **User services** are managed over the session bus: no password is ever requested.
- **System services** are managed over the system bus with polkit interactive authorization: your desktop's native authentication dialog appears **only** when you perform a privileged action (start, stop, edit, …). Browsing services, status and logs never asks for a password.
- **Writing system unit files** goes through a small, auditable helper launched via `pkexec`, which accepts only a fixed set of operations and only paths under `/etc/systemd/system`. Its polkit action uses `auth_admin_keep`, so saving a file and the `daemon-reload` that follows ask for the password once; to be asked every time, change `auth_admin_keep` to `auth_admin` in `/usr/share/polkit-1/actions/eu.nicop.unitdeck.policy`.
- UnitDeck never reads, stores or handles your password: authentication is entirely delegated to polkit.

## Requirements

- A Linux distribution with **systemd** and **polkit** (primary target: recent Ubuntu releases with GNOME, on X11 or Wayland). The `.deb` package is built on **Ubuntu 24.04 LTS**, the oldest supported release.
- A polkit authentication agent (included in all major desktop environments).

## Installation

Download the package for your distribution from the [Releases page](https://github.com/n1c0p/UnitDeck/releases) and install it:

```bash
sudo apt install ./unitdeck_<version>_amd64.deb        # Ubuntu 24.04+, Debian 13+
sudo dnf install ./unitdeck-<version>-1.x86_64.rpm     # Fedora 40+
sudo zypper install --allow-unsigned-rpm ./unitdeck-<version>-1.x86_64.rpm   # openSUSE Tumbleweed
```

Both packages hold the same bundle, built on Ubuntu 24.04 (glibc 2.39): any distribution with a newer glibc works, openSUSE Leap 15 does not.

### Build and install from source

UnitDeck is written in **Python 3.12+** with **PyQt6**. Two ways, both starting from a clone:

```bash
git clone https://github.com/n1c0p/UnitDeck.git
cd UnitDeck
```

**Package built locally (recommended).** Same result as the published package, removable with the package manager. Build on Ubuntu 24.04 or newer:

```bash
sudo apt install git python3 python3-venv libpython3.12 binutils lintian
python3 -m venv .venv
.venv/bin/pip install . pyinstaller
PYTHON=.venv/bin/python packaging/build-deb.sh
sudo apt install ./dist/unitdeck_*.deb
```

On Fedora install `python3 rpm-build binutils` instead and run `packaging/build-rpm.sh`, then `sudo dnf install ./dist/unitdeck-*.rpm`.

`packaging/stage.sh` bundles the application with PyInstaller (`unitdeck.spec`, one-directory mode) into `/opt/unitdeck` and adds the helper, the polkit policy, the desktop file, the icon and a man page; `build-deb.sh` turns that tree into the `.deb` with `dpkg-deb`, checked by `lintian` (a few tags accepted by design are listed in `packaging/lintian-suppress`), `build-rpm.sh` into the `.rpm` with `rpmbuild` (`packaging/unitdeck.rpm.spec`, dependencies by library soname). `packaging/test-install.sh` installs the result in a clean Ubuntu 24.04 or Fedora 41 container and runs `unitdeck --check`. Uninstall with `sudo apt remove unitdeck`.

**Manual, without PyInstaller.** A virtual environment runs the application; the helper and its polkit policy, needed only to edit system unit files, are installed once with a script:

```bash
python3 -m venv .venv
.venv/bin/pip install .
packaging/install-dev-helper.sh      # asks for sudo; "uninstall" removes them
.venv/bin/unitdeck
```

For a launcher in the applications menu, create `~/.local/share/applications/eu.nicop.unitdeck.desktop` from `packaging/eu.nicop.unitdeck.desktop` with `Exec=` pointing at `.venv/bin/unitdeck` and `Icon=` at `packaging/icons/eu.nicop.unitdeck.svg` (absolute paths). The version number comes from git tags via `setuptools-scm`: a checkout between releases reports a development version.

Either way the machine needs systemd, polkit with a desktop authentication agent, `pkexec`, `systemd-analyze` and `journalctl`, all present on a standard Ubuntu desktop. Every push to `develop` builds a preview package, kept 14 days as a workflow artifact; every merge into `main` publishes a release (see CONTRIBUTING).

## Usage

The **System services** and **User services** tabs list every `.service` unit of the system manager and of your user session, including installed units that are not loaded. Browsing, states and logs never ask for a password; the first privileged action on a system service (start, stop, enable, …) opens the desktop's polkit dialog, and cancelling it simply leaves the service as it was. Each row has start, stop and restart buttons plus a "⋯" menu with reload, enable/disable at boot, mask/unmask and logs. The same actions are available from the right-click menu and, on the selected row, from the keyboard:

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Start |
| `Ctrl+T` | Stop |
| `Ctrl+R` | Restart |
| `Ctrl+L` | Show logs (also double-click) |

### Editing a service

*Edit* (`Ctrl+E`) opens an editor with syntax highlighting and line numbers next to the effective configuration (unit file plus every drop-in, with their paths). For a unit shipped by a package the editor writes a drop-in `override.conf` under `/etc/systemd/system/<unit>.d/` (or `~/.config/systemd/user/<unit>.d/` for user services): only the directives you change go there, and package upgrades keep working. A checkbox switches to a full copy of the unit instead, which shadows the package file. Units created by you are edited in place. Before saving, the file is checked with `systemd-analyze verify` and warnings are shown; the previous file is kept as `.bak`; after saving UnitDeck runs `daemon-reload` and offers to restart the service. *Restore original* removes drop-ins and local copies of a package unit (like `systemctl revert`), *Delete* stops, disables and removes a unit you created.

### Creating a service

*New service* opens a four-step wizard: name and template, guided fields (description, command, type, restart policy, dependencies, and for system services the optional `User=`/`Group=`, without which the service runs as root), an editable preview checked with `systemd-analyze verify`, and the final "enable at boot" / "start now" options. The unit is written to `~/.config/systemd/user/` from the user tab or to `/etc/systemd/system/` from the system tab (through the helper, so polkit asks for your password). Names already used by any unit in systemd's search paths are refused.

Templates are plain files in `src/unitdeck/templates/`: an empty service, a one-shot task with `RemainAfterExit`, a long-running service with `Restart=on-failure`, and, for user services only, an SMB share mounted with `gio` (it needs a user session with D-Bus). Adding one is a small pull request, see CONTRIBUTING.

### Lingering

The user tab has a *Linger* switch: when on, your user services keep running without an open session (what `loginctl enable-linger` does). Changing it goes through logind and asks for authorization.

System logs are readable without a password only if your user belongs to the `adm` or `systemd-journal` group (the default for the first user on Ubuntu); otherwise the log window shows journalctl's hint.

The table follows systemd's D-Bus signals, so states update by themselves. "Reload configuration" runs a `daemon-reload` after you edit unit files on disk.

The interface is available in English and Italian: it follows the desktop language by default and can be changed from *Settings → Language*.

### Updates

At startup UnitDeck asks the GitHub Releases API (`api.github.com`) whether a newer version exists; nothing else is sent. Turn this off with *Settings → Check for updates at startup*, or check by hand from *Info → Check for updates…*. When an update is available you can read the release notes, download the package for your distribution (`.deb` or `.rpm`, chosen from `/etc/os-release`; its SHA256 is verified against the checksum published with the release) and install it: the installation runs `apt-get`, `dnf` or `zypper` through `pkexec`, so the desktop asks for your password. Checks are skipped when running a development version from source.

## Dependencies and licenses

All dependencies are compatible with the GPL-3.0-or-later license of the project.

| Package | Role | License |
|---------|------|---------|
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) | GUI toolkit and D-Bus bindings (QtDBus) | GPL-3.0-only |
| [setuptools-scm](https://github.com/pypa/setuptools-scm) | Version from git tags (build time only) | MIT |
| [pytest](https://pytest.org/) | Tests (development only) | MIT |
| [ruff](https://docs.astral.sh/ruff/) | Lint and format (development only) | MIT |
| [reuse](https://reuse.software/) | License compliance check (development only) | Apache-2.0 / GPL-3.0-or-later |
| [PyInstaller](https://pyinstaller.org/) | Bundles the application for the `.deb` (build only) | GPL-2.0-or-later with bootloader exception |

## Contributing

Contributions are welcome. The repository uses two long-lived branches:

- `main`: always matches the latest release;
- `develop`: ongoing development, the target for all pull requests.

Start your work from `develop` in a `feature/*` or `fix/*` branch and open a pull request against `develop`. [CONTRIBUTING.md](https://github.com/n1c0p/UnitDeck/blob/main/CONTRIBUTING.md) describes the full workflow: branches, pull requests, SPDX headers, how a release is prepared and which GitHub rulesets protect `main`, `develop` and the `v*` tags.

Please read [CODE_OF_CONDUCT.md](https://github.com/n1c0p/UnitDeck/blob/main/CODE_OF_CONDUCT.md); security problems go through [SECURITY.md](https://github.com/n1c0p/UnitDeck/blob/main/SECURITY.md), not public issues.

Documentation is kept in English and Italian: when you change `README.md` or `CHANGELOG.md`, please update `README.it.md` and `CHANGELOG.it.md` as well. If you are not comfortable with Italian, just mention it in the pull request and the maintainer will take care of the translation.

Releases are automatic: a pull request from `develop` to `main` sets the version in both changelogs, and merging it tags the commit, builds the `.deb` and publishes the GitHub Release.

Service templates are plain files in the repository: adding a new one through a pull request is a great first contribution.

## Changelog

All notable changes are listed in [CHANGELOG.md](https://github.com/n1c0p/UnitDeck/blob/main/CHANGELOG.md).

## License

Copyright (C) 2026 Nicola Palmieri ([n1c0p](https://github.com/n1c0p))

UnitDeck is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

UnitDeck is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the [GNU General Public License](https://github.com/n1c0p/UnitDeck/blob/main/LICENSE) for more details.
