#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
#
# Build dist/unitdeck_<version>_amd64.deb from the staging tree made by packaging/stage.sh
# (run automatically unless REUSE_STAGE=1 and build/stage exists). Requires dpkg-deb; lintian
# runs when available.
set -eu
cd "$(dirname "$0")/.."
if [ -z "${REUSE_STAGE:-}" ] || [ ! -d build/stage ]; then
    packaging/stage.sh
fi
VERSION="$(cat build/VERSION)"
ARCH="$(dpkg --print-architecture)"
STAGE=build/deb
DEB="dist/unitdeck_${VERSION}_${ARCH}.deb"
MAINTAINER="${DEB_MAINTAINER:-Nicola Palmieri <npalmieri@hotmail.com>}"

echo "==> Debian metadata"
rm -rf "$STAGE"
cp -a build/stage "$STAGE"
mkdir -p "$STAGE/DEBIAN"
install -m 0755 packaging/postinst packaging/postrm "$STAGE/DEBIAN/"
printf 'unitdeck (%s) stable; urgency=medium\n\n  * See https://github.com/n1c0p/UnitDeck/blob/main/CHANGELOG.md\n\n -- %s  %s\n' \
    "$VERSION" "$MAINTAINER" "$(date -R)" | gzip -9n > "$STAGE/usr/share/doc/unitdeck/changelog.gz"

SIZE="$(du -sk "$STAGE" --exclude=DEBIAN | cut -f1)"
cat > "$STAGE/DEBIAN/control" <<CONTROL
Package: unitdeck
Version: $VERSION
Section: admin
Priority: optional
Architecture: $ARCH
Installed-Size: $SIZE
Maintainer: $MAINTAINER
Homepage: https://github.com/n1c0p/UnitDeck
Depends: python3, pkexec, polkitd | policykit-1, systemd, libc6 (>= 2.39), libxcb-cursor0, libegl1, libgl1, libxkbcommon0, libxkbcommon-x11-0, libdbus-1-3, libfontconfig1, libfreetype6, libglib2.0-0t64 | libglib2.0-0, libgssapi-krb5-2, libssl3t64 | libssl3, zlib1g, liblzma5, libzstd1, libexpat1, libffi8, libx11-6, libx11-xcb1, libxcb1, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-sync1, libxcb-xfixes0, libxcb-xkb1, libxcb-util1, libwayland-client0, libwayland-cursor0, libwayland-egl1
Recommends: xdg-utils, libgtk-3-0t64 | libgtk-3-0
Description: Desktop application to manage systemd services
 UnitDeck manages systemd system and user services from a graphical
 interface: start, stop, restart, enable, mask, edit with drop-ins, create
 from templates and read the journal, with live updates over D-Bus.
 .
 The interface runs as a normal user: privileged actions are authorized
 through polkit, and system unit files are written by a small helper
 launched with pkexec.
CONTROL

echo "==> dpkg-deb"
mkdir -p dist
rm -f "$DEB"
dpkg-deb --root-owner-group --build "$STAGE" "$DEB"
ls -l "$DEB"
if command -v lintian >/dev/null 2>&1; then
    echo "==> lintian"
    lintian --fail-on error,warning --suppress-tags-from-file packaging/lintian-suppress "$DEB"
fi
echo "$DEB"
