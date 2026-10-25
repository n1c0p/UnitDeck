#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
#
# Build dist/unitdeck-<version>-1.x86_64.rpm from the staging tree made by packaging/stage.sh
# (run automatically unless REUSE_STAGE=1 and build/stage exists). Requires rpmbuild (apt
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
RPM="$(find "$TOPDIR/RPMS" -name 'unitdeck-*.rpm' | head -n1)"
cp "$RPM" dist/
ls -l "dist/$(basename "$RPM")"
echo "dist/$(basename "$RPM")"
