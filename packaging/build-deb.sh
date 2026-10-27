#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
#
# Build the three Debian packages from the staging trees made by packaging/stage.sh (run
# automatically unless REUSE_STAGE=1 and build/stage exists):
#   unitdeck-common_<v>_amd64.deb   helper, polkit policy
#   unitdeck_<v>_amd64.deb          desktop application  (Depends: unitdeck-common)
#   unitdeck-tui_<v>_amd64.deb      terminal interface   (Depends: unitdeck-common)
# Requires dpkg-deb; lintian runs when available.
set -eu
cd "$(dirname "$0")/.."
if [ -z "${REUSE_STAGE:-}" ] || [ ! -d build/stage ]; then
    packaging/stage.sh
fi
VERSION="$(cat build/VERSION)"
ARCH="$(dpkg --print-architecture)"
MAINTAINER="${DEB_MAINTAINER:-Nicola Palmieri <npalmieri@hotmail.com>}"
mkdir -p dist

QT_LIBS="libxcb-cursor0, libegl1, libgl1, libxkbcommon0, libxkbcommon-x11-0, libdbus-1-3, libfontconfig1, libfreetype6, libglib2.0-0t64 | libglib2.0-0, libx11-6, libx11-xcb1, libxcb1, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-sync1, libxcb-xfixes0, libxcb-xkb1, libxcb-util1, libwayland-client0, libwayland-cursor0, libwayland-egl1"
PY_LIBS="libc6 (>= 2.39), libgssapi-krb5-2, libssl3t64 | libssl3, zlib1g, liblzma5, libzstd1, libexpat1, libffi8"

build() {  # build TREE PACKAGE DEPENDS RECOMMENDS DESCRIPTION-FILE
    tree="$1"; package="$2"; depends="$3"; recommends="$4"; description="$5"
    stage="build/deb/$package"
    deb="dist/${package}_${VERSION}_${ARCH}.deb"
    rm -rf "$stage"; mkdir -p build/deb
    cp -a "build/stage/$tree" "$stage"
    mkdir -p "$stage/DEBIAN" "$stage/usr/share/doc/$package"
    printf '%s (%s) stable; urgency=medium\n\n  * See https://github.com/n1c0p/UnitDeck/blob/main/CHANGELOG.md\n\n -- %s  %s\n' \
        "$package" "$VERSION" "$MAINTAINER" "$(date -R)" | gzip -9n > "$stage/usr/share/doc/$package/changelog.gz"
    if [ "$tree" = gui ]; then
        install -m 0755 packaging/postinst packaging/postrm "$stage/DEBIAN/"
    fi
    size="$(du -sk "$stage" --exclude=DEBIAN | cut -f1)"
    {
        printf 'Package: %s\nVersion: %s\nSection: admin\nPriority: optional\nArchitecture: %s\n' "$package" "$VERSION" "$ARCH"
        printf 'Installed-Size: %s\nMaintainer: %s\nHomepage: https://github.com/n1c0p/UnitDeck\n' "$size" "$MAINTAINER"
        printf 'Depends: %s\n' "$depends"
        [ -n "$recommends" ] && printf 'Recommends: %s\n' "$recommends"
        # The helper and the policy lived in unitdeck before 0.3.0: let dpkg hand them over
        # (no Breaks: the 0.2.0 updater installs this package alone and must not lose the GUI).
        [ "$package" = unitdeck-common ] && printf 'Replaces: unitdeck (<< 0.3.0)\n'
        printf 'Description: %s\n' "$description"
    } > "$stage/DEBIAN/control"
    rm -f "$deb"
    dpkg-deb --root-owner-group --build "$stage" "$deb" >/dev/null
    ls -l "$deb"
}

build common unitdeck-common "python3, pkexec, polkitd | policykit-1, systemd" "" \
"Privileged helper and polkit policy of UnitDeck
 The helper writes system unit files under /etc/systemd/system on behalf of
 the UnitDeck interfaces, launched through pkexec and limited to a fixed set
 of operations. Install unitdeck (desktop) or unitdeck-tui (terminal)."

build gui unitdeck "unitdeck-common (= $VERSION), $PY_LIBS, $QT_LIBS" "xdg-utils, libgtk-3-0t64 | libgtk-3-0" \
"Desktop application to manage systemd services
 UnitDeck manages systemd system and user services from a graphical
 interface: start, stop, restart, enable, mask, edit with drop-ins, create
 from templates and read the journal, with live updates over D-Bus.
 .
 The interface runs as a normal user: privileged actions are authorized
 through polkit, and system unit files are written by a small helper
 launched with pkexec."

build tui unitdeck-tui "unitdeck-common (= $VERSION), $PY_LIBS" "" \
"Terminal interface to manage systemd services
 The htop-like terminal version of UnitDeck: system and user services,
 search, filters, single-key actions, logs, editor with drop-ins, new
 service from templates. Works over SSH and on a TTY, where polkit asks
 for the password through pkttyagent."

if command -v lintian >/dev/null 2>&1; then
    echo "==> lintian"
    lintian --fail-on error,warning --suppress-tags-from-file packaging/lintian-suppress dist/unitdeck*_"${VERSION}"_*.deb
fi
