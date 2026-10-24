<!--
SPDX-License-Identifier: GPL-3.0-or-later
SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
-->

# Security policy

**English** | [Italiano](SECURITY.it.md)

## Supported versions

Only the latest release published on the [Releases page](https://github.com/n1c0p/UnitDeck/releases) receives fixes.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Report it privately through [GitHub's vulnerability reporting](https://github.com/n1c0p/UnitDeck/security/advisories/new) or by e-mail to npalmieri@hotmail.com. You will get an answer within a week; the fix is published as a new release and credited to you unless you prefer otherwise.

## What matters most

UnitDeck runs as a normal user and delegates every privileged action to polkit. The parts worth a careful look are:

- `helper/unitdeck-helper`, the only code that runs as root (through `pkexec`): it must accept nothing but the documented operations under `/etc/systemd/system`;
- `packaging/eu.nicop.unitdeck.policy`, the polkit policy that pins the helper's path;
- the D-Bus calls with interactive authorization on the system bus;
- the update mechanism (download, SHA256 verification, `pkexec apt-get`).
