# UnitDeck

**English** | [Italiano](README.it.md)

[![License: GPL v3+](https://img.shields.io/badge/License-GPLv3%2B-blue.svg)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/n1c0p/UnitDeck?include_prereleases&sort=semver)](https://github.com/n1c0p/UnitDeck/releases)

**UnitDeck** is a desktop application for Linux to manage **systemd services**, both **system-wide** and **per-user**, from a clean graphical interface.

> 🚧 **Status: early development.** No release is available yet. The features below describe the planned scope of the first versions.

## Why UnitDeck

Managing services usually means juggling `systemctl`, `systemctl --user`, `journalctl` and an editor opened with `sudo`. UnitDeck brings all of it into a single window, without ever running the interface as root.

## Planned features

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
- **Writing system unit files** goes through a small, auditable helper launched via `pkexec`, which accepts only a fixed set of operations and only paths under `/etc/systemd/system`.
- UnitDeck never reads, stores or handles your password: authentication is entirely delegated to polkit.

## Requirements

- A Linux distribution with **systemd** and **polkit** (primary target: recent Ubuntu releases with GNOME, on X11 or Wayland). The `.deb` package is built on **Ubuntu 24.04 LTS**, the oldest supported release.
- A polkit authentication agent (included in all major desktop environments).

## Installation

Once the first release is published, download the `.deb` package from the [Releases page](https://github.com/n1c0p/UnitDeck/releases) and install it:

```bash
sudo apt install ./unitdeck_<version>_amd64.deb
```

### From source

UnitDeck is written in **Python 3.12+** with **PyQt6**.

```bash
git clone https://github.com/n1c0p/UnitDeck.git
cd UnitDeck
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unitdeck
```

The version number comes from git tags via `setuptools-scm`: a checkout between releases reports a development version.

## Usage

The **User services** tab lists every `.service` unit of your user session, including installed units that are not loaded. Each row has start, stop and restart buttons plus a "⋯" menu with reload, enable/disable at boot, mask/unmask and logs. The same actions are available from the right-click menu and, on the selected row, from the keyboard:

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Start |
| `Ctrl+T` | Stop |
| `Ctrl+R` | Restart |
| `Ctrl+L` | Show logs (also double-click) |

The table follows systemd's D-Bus signals, so states update by themselves. "Reload configuration" runs a `daemon-reload` after you edit unit files on disk.

The interface is available in English and Italian: it follows the desktop language by default and can be changed from *Settings → Language*.

### Updates

At startup UnitDeck asks the GitHub Releases API (`api.github.com`) whether a newer version exists; nothing else is sent. Turn this off with *Settings → Check for updates at startup*, or check by hand from *Info → Check for updates…*. When an update is available you can read the release notes, download the `.deb` (its SHA256 is verified against the checksum published with the release) and install it: the installation runs `apt-get` through `pkexec`, so the desktop asks for your password. Checks are skipped when running a development version from source.

## Dependencies and licenses

All dependencies are compatible with the GPL-3.0-or-later license of the project.

| Package | Role | License |
|---------|------|---------|
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) | GUI toolkit and D-Bus bindings (QtDBus) | GPL-3.0-only |
| [setuptools-scm](https://github.com/pypa/setuptools-scm) | Version from git tags (build time only) | MIT |
| [pytest](https://pytest.org/) | Tests (development only) | MIT |
| [ruff](https://docs.astral.sh/ruff/) | Lint and format (development only) | MIT |
| [reuse](https://reuse.software/) | License compliance check (development only) | Apache-2.0 / GPL-3.0-or-later |

## Contributing

Contributions are welcome. The repository uses two long-lived branches:

- `main`: always matches the latest release;
- `develop`: ongoing development, the target for all pull requests.

Start your work from `develop` in a `feature/*` or `fix/*` branch and open a pull request against `develop`. [CONTRIBUTING.md](CONTRIBUTING.md) describes the full workflow: branches, pull requests, SPDX headers, how a release is prepared and which GitHub rulesets protect `main`, `develop` and the `v*` tags.

Documentation is kept in English and Italian: when you change `README.md` or `CHANGELOG.md`, please update `README.it.md` and `CHANGELOG.it.md` as well. If you are not comfortable with Italian, just mention it in the pull request and the maintainer will take care of the translation.

Releases are automatic: a pull request from `develop` to `main` sets the version in both changelogs, and merging it tags the commit, builds the `.deb` and publishes the GitHub Release.

Service templates are plain files in the repository: adding a new one through a pull request is a great first contribution.

## Changelog

All notable changes are listed in [CHANGELOG.md](CHANGELOG.md).

## License

Copyright (C) 2026 Nicola ([n1c0p](https://github.com/n1c0p))

UnitDeck is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

UnitDeck is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the [GNU General Public License](LICENSE) for more details.
