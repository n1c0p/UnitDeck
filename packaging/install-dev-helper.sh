#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
#
# Development only: install (or remove with "uninstall") the privileged helper and its polkit
# policy from this checkout, so that writing system unit files works without the .deb package.
set -eu
cd "$(dirname "$0")/.."
if [ "${1:-install}" = "uninstall" ]; then
    sudo rm -f /usr/libexec/unitdeck/unitdeck-helper /usr/share/polkit-1/actions/eu.nicop.unitdeck.policy
    sudo rmdir /usr/libexec/unitdeck 2>/dev/null || true
    echo "helper and policy removed"
else
    sudo install -D -m 0755 helper/unitdeck-helper /usr/libexec/unitdeck/unitdeck-helper
    sudo install -D -m 0644 packaging/eu.nicop.unitdeck.policy /usr/share/polkit-1/actions/eu.nicop.unitdeck.policy
    echo "helper installed in /usr/libexec/unitdeck, policy in /usr/share/polkit-1/actions"
fi
