#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
#
# Build dist/unitdeck_<version>_amd64.deb from this checkout: PyInstaller one-dir bundle in
# /opt/unitdeck, helper script in /usr/libexec, polkit policy, desktop file and icon.
# Run it on the oldest supported Ubuntu (24.04) so the bundle works on newer glibc too.
# Requires: the package installed in the active Python (pip install -e .), pyinstaller, dpkg-deb.
set -eu
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
VERSION="$("$PYTHON" -c 'import unitdeck; print(unitdeck.__version__)')"
ARCH="$(dpkg --print-architecture)"
STAGE=build/deb
DEB="dist/unitdeck_${VERSION}_${ARCH}.deb"
MAINTAINER="${DEB_MAINTAINER:-Nicola Palmieri <npalmieri@hotmail.com>}"

echo "==> PyInstaller bundle (version $VERSION)"
"$PYTHON" -m PyInstaller --noconfirm --clean --log-level WARN unitdeck.spec

echo "==> staging"
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" "$STAGE/opt" "$STAGE/usr/bin" "$STAGE/usr/libexec/unitdeck" \
    "$STAGE/usr/share/applications" "$STAGE/usr/share/icons/hicolor/scalable/apps" \
    "$STAGE/usr/share/polkit-1/actions" "$STAGE/usr/share/doc/unitdeck" "$STAGE/usr/share/man/man1"
cp -a dist/unitdeck "$STAGE/opt/unitdeck"
ln -s /opt/unitdeck/unitdeck "$STAGE/usr/bin/unitdeck"
install -m 0755 helper/unitdeck-helper "$STAGE/usr/libexec/unitdeck/unitdeck-helper"
install -m 0644 packaging/eu.nicop.unitdeck.desktop "$STAGE/usr/share/applications/"
install -m 0644 packaging/icons/eu.nicop.unitdeck.svg "$STAGE/usr/share/icons/hicolor/scalable/apps/"
install -m 0644 packaging/eu.nicop.unitdeck.policy "$STAGE/usr/share/polkit-1/actions/"
install -m 0644 packaging/copyright "$STAGE/usr/share/doc/unitdeck/copyright"
gzip -9n -c packaging/unitdeck.1 > "$STAGE/usr/share/man/man1/unitdeck.1.gz"
install -m 0755 packaging/postinst packaging/postrm "$STAGE/DEBIAN/"
printf 'unitdeck (%s) stable; urgency=medium\n\n  * See https://github.com/n1c0p/UnitDeck/blob/main/CHANGELOG.md\n\n -- %s  %s\n' \
    "$VERSION" "$MAINTAINER" "$(date -R)" | gzip -9n > "$STAGE/usr/share/doc/unitdeck/changelog.gz"
find "$STAGE" -type d -exec chmod 0755 {} +
find "$STAGE/opt/unitdeck" -type f ! -perm -u=x -exec chmod 0644 {} +
find "$STAGE/opt/unitdeck" -type f -perm -u=x -exec chmod 0755 {} +
find "$STAGE/opt/unitdeck" -type f -name "*.so*" -exec chmod 0644 {} +  # shared libraries need no x bit

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
Depends: python3, pkexec, polkitd | policykit-1, systemd, libc6 (>= 2.39), libxcb-cursor0, libegl1, libgl1, libxkbcommon0, libxkbcommon-x11-0, libdbus-1-3, libfontconfig1, libfreetype6, libglib2.0-0t64 | libglib2.0-0, libgssapi-krb5-2, libssl3t64 | libssl3, zlib1g, libbz2-1.0, liblzma5, libzstd1, libexpat1, libffi8, libx11-6, libx11-xcb1, libxcb1, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-sync1, libxcb-xfixes0, libxcb-xkb1, libxcb-util1, libwayland-client0, libwayland-cursor0, libwayland-egl1
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
