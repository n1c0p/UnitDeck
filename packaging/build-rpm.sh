#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
#
# Build the three RPM packages (unitdeck-common, unitdeck, unitdeck-tui) from the staging trees
# made by packaging/stage.sh (run automatically unless REUSE_STAGE=1 and build/stage exists). Requires rpmbuild (apt
# package "rpm" on Ubuntu). Dependencies are declared by shared-library soname, so the same
# package installs on Fedora 40+ and openSUSE Tumbleweed (glibc >= 2.39).
set -eu
cd "$(dirname "$0")/.."
if [ -z "${REUSE_STAGE:-}" ] || [ ! -d build/stage ]; then
    packaging/stage.sh
fi
VERSION="$(cat build/VERSION)"
RPM_VERSION="$(printf '%s' "$VERSION" | tr '+-' '..')"  # rpm versions take neither '-' nor '+'
TOPDIR="$PWD/build/rpm"

echo "==> rpmbuild (version $RPM_VERSION)"
rm -rf "$TOPDIR"
mkdir -p "$TOPDIR/BUILD" "$TOPDIR/RPMS" "$TOPDIR/SPECS" dist
rpmbuild -bb packaging/unitdeck.rpm.spec \
    --define "_topdir $TOPDIR" \
    --define "_version $RPM_VERSION" \
    --define "_stage $PWD/build/stage" \
    --quiet
find "$TOPDIR/RPMS" -name 'unitdeck*.rpm' -exec cp {} dist/ \;
ls -l dist/unitdeck*-"$RPM_VERSION"-1.x86_64.rpm
