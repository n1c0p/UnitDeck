#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
#
# Common staging for the .deb and .rpm packages, three trees under build/stage/:
#   common  helper script in /usr/libexec, polkit policy, copyright   (package unitdeck-common)
#   gui     PyInstaller bundle in /opt/unitdeck, /usr/bin link, desktop file, icon, man page
#   tui     PyInstaller bundle in /opt/unitdeck-tui, /usr/bin link, man page
# The version goes to build/VERSION. Run it on the oldest supported Ubuntu (24.04) so the
# bundles work on newer glibc too. Requires: pip install ".[gui,tui]" pyinstaller.
set -eu
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
VERSION="$("$PYTHON" -c 'import unitdeck; print(unitdeck.__version__)')"
STAGE=build/stage
rm -rf "$STAGE"

bundle() {  # bundle NAME SPEC: PyInstaller one-dir bundle into $STAGE/$1/opt/<name>
    echo "==> PyInstaller $2 (version $VERSION)"
    "$PYTHON" -m PyInstaller --noconfirm --clean --log-level WARN "$2"
}
doc() {  # doc TREE PACKAGE: copyright under /usr/share/doc/<package>
    mkdir -p "$STAGE/$1/usr/share/doc/$2"
    install -m 0644 packaging/copyright "$STAGE/$1/usr/share/doc/$2/copyright"
}
man() {  # man TREE SOURCE: gzipped man page in section 1
    mkdir -p "$STAGE/$1/usr/share/man/man1"
    gzip -9n -c "packaging/$2" > "$STAGE/$1/usr/share/man/man1/$2.gz"
}
tidy() {  # tidy DIR: directories 755, files 644 unless executable, shared libraries never executable
    find "$1" -type d -exec chmod 0755 {} +
    find "$1" -type f ! -perm -u=x -exec chmod 0644 {} +
    find "$1" -type f -perm -u=x -exec chmod 0755 {} +
    find "$1" -type f -name "*.so*" -exec chmod 0644 {} +
}

echo "==> common"
mkdir -p "$STAGE/common/usr/libexec/unitdeck" "$STAGE/common/usr/share/polkit-1/actions"
install -m 0755 helper/unitdeck-helper "$STAGE/common/usr/libexec/unitdeck/unitdeck-helper"
install -m 0644 packaging/eu.nicop.unitdeck.policy "$STAGE/common/usr/share/polkit-1/actions/"
doc common unitdeck-common

bundle unitdeck unitdeck.spec
mkdir -p "$STAGE/gui/opt" "$STAGE/gui/usr/bin" "$STAGE/gui/usr/share/applications" \
    "$STAGE/gui/usr/share/icons/hicolor/scalable/apps"
cp -a dist/unitdeck "$STAGE/gui/opt/unitdeck"
ln -s /opt/unitdeck/unitdeck "$STAGE/gui/usr/bin/unitdeck"
install -m 0644 packaging/eu.nicop.unitdeck.desktop "$STAGE/gui/usr/share/applications/"
install -m 0644 packaging/icons/eu.nicop.unitdeck.svg "$STAGE/gui/usr/share/icons/hicolor/scalable/apps/"
doc gui unitdeck
man gui unitdeck.1
tidy "$STAGE/gui/opt/unitdeck"

bundle unitdeck-tui unitdeck-tui.spec
mkdir -p "$STAGE/tui/opt" "$STAGE/tui/usr/bin"
cp -a dist/unitdeck-tui "$STAGE/tui/opt/unitdeck-tui"
ln -s /opt/unitdeck-tui/unitdeck-tui "$STAGE/tui/usr/bin/unitdeck-tui"
doc tui unitdeck-tui
man tui unitdeck-tui.1
tidy "$STAGE/tui/opt/unitdeck-tui"

find "$STAGE" -type d -exec chmod 0755 {} +
printf '%s\n' "$VERSION" > build/VERSION
echo "staged version $VERSION"
