#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
#
# Common staging for the .deb and .rpm packages: PyInstaller one-dir bundle in /opt/unitdeck,
# /usr/bin link, helper script in /usr/libexec, polkit policy, desktop file, icon, man page and
# copyright, laid out under build/stage/. The version goes to build/VERSION.
# Run it on the oldest supported Ubuntu (24.04) so the bundle works on newer glibc too.
# Requires: the package installed in the active Python (pip install .), pyinstaller.
set -eu
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
VERSION="$("$PYTHON" -c 'import unitdeck; print(unitdeck.__version__)')"
STAGE=build/stage

echo "==> PyInstaller bundle (version $VERSION)"
"$PYTHON" -m PyInstaller --noconfirm --clean --log-level WARN unitdeck.spec

echo "==> staging in $STAGE"
rm -rf "$STAGE"
mkdir -p "$STAGE/opt" "$STAGE/usr/bin" "$STAGE/usr/libexec/unitdeck" \
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
find "$STAGE" -type d -exec chmod 0755 {} +
find "$STAGE/opt/unitdeck" -type f ! -perm -u=x -exec chmod 0644 {} +
find "$STAGE/opt/unitdeck" -type f -perm -u=x -exec chmod 0755 {} +
find "$STAGE/opt/unitdeck" -type f -name "*.so*" -exec chmod 0644 {} +  # shared libraries need no x bit
printf '%s\n' "$VERSION" > build/VERSION
echo "staged version $VERSION"
