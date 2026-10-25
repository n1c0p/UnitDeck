#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
#
# Install the given package in a clean container (Docker) and run the smoke checks as a normal
# user: --version, --check (Qt loads offscreen), the helper refuses a bad name, every bundled
# library resolves. A .deb is tested on ubuntu:24.04, an .rpm on fedora:41.
set -eu
PKG="$(realpath "$1")"
NAME="$(basename "$PKG")"
case "$NAME" in
    *.deb)
        IMAGE=ubuntu:24.04
        INSTALL='export DEBIAN_FRONTEND=noninteractive; apt-get update -qq >/dev/null; apt-get install -y -qq --no-install-recommends /pkg/'"$NAME"' >/dev/null'
        ;;
    *.rpm)
        IMAGE=fedora:41
        # util-linux brings runuser, absent from the minimal image
        INSTALL='dnf install -y -q --setopt=install_weak_deps=False /pkg/'"$NAME"' util-linux >/dev/null 2>&1; useradd -m ubuntu'
        ;;
    *) echo "unknown package type: $NAME" >&2; exit 2 ;;
esac
docker run --rm -v "$(dirname "$PKG"):/pkg:ro" "$IMAGE" sh -c '
set -e
'"$INSTALL"'
runuser -u ubuntu -- unitdeck --version
QT_QPA_PLATFORM=offscreen runuser -u ubuntu -- unitdeck --check
if /usr/libexec/unitdeck/unitdeck-helper write-unit ../x.service </dev/null 2>/dev/null; then
    echo "helper accepted a bad unit name"; exit 1
fi
# Every bundled library must resolve, except optional plugins Qt loads only when their
# desktop (GTK) libraries are present: those are Recommends, not Depends. The bootloader
# puts _internal on the library path at runtime, so ldd gets the same.
missing="$(find /opt/unitdeck -name "*.so*" -not -path "*/platformthemes/*" | while read -r lib; do
    LD_LIBRARY_PATH=/opt/unitdeck/_internal ldd "$lib" 2>/dev/null | grep "not found" | sed "s|^|$lib: |"; done | sort -u || true)"
if [ -n "$missing" ]; then echo "unresolved libraries:"; echo "$missing"; exit 1; fi
echo "clean install OK ('"$NAME"')"
'
