#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
#
# Install the given packages (the three of one format, same directory) in a clean container
# (Docker) and run the smoke checks as a normal user: --version and --check (Qt loads offscreen)
# of the desktop application, --version and --check of the terminal one, the helper refuses a bad name,
# every bundled library resolves. .deb files are tested on ubuntu:24.04, .rpm on fedora:41.
set -eu
DIR="$(realpath "$(dirname "$1")")"
NAMES=""
for pkg in "$@"; do NAMES="$NAMES /pkg/$(basename "$pkg")"; done
case "$1" in
    *.deb)
        IMAGE=ubuntu:24.04
        INSTALL='export DEBIAN_FRONTEND=noninteractive; apt-get update -qq >/dev/null; apt-get install -y -qq --no-install-recommends'"$NAMES"' >/dev/null'
        ;;
    *.rpm)
        IMAGE=fedora:41
        # util-linux brings runuser, absent from the minimal image
        INSTALL='dnf install -y -q --setopt=install_weak_deps=False'"$NAMES"' util-linux >/dev/null 2>&1; useradd -m ubuntu'
        ;;
    *) echo "unknown package type: $1" >&2; exit 2 ;;
esac
docker run --rm -v "$DIR:/pkg:ro" "$IMAGE" sh -c '
set -e
'"$INSTALL"'
runuser -u ubuntu -- unitdeck --version
QT_QPA_PLATFORM=offscreen runuser -u ubuntu -- unitdeck --check
runuser -u ubuntu -- unitdeck-tui --version
runuser -u ubuntu -- unitdeck-tui --check
test -x /usr/libexec/unitdeck/unitdeck-helper
if /usr/libexec/unitdeck/unitdeck-helper write-unit ../x.service </dev/null 2>/dev/null; then
    echo "helper accepted a bad unit name"; exit 1
fi
# Every bundled library must resolve, except optional plugins Qt loads only when their
# desktop (GTK) libraries are present: those are Recommends, not Depends. The bootloader
# puts _internal on the library path at runtime, so ldd gets the same.
missing="$(for app in unitdeck unitdeck-tui; do find /opt/$app -name "*.so*" -not -path "*/platformthemes/*" | while read -r lib; do
    LD_LIBRARY_PATH=/opt/$app/_internal ldd "$lib" 2>/dev/null | grep "not found" | sed "s|^|$lib: |"; done; done | sort -u || true)"
if [ -n "$missing" ]; then echo "unresolved libraries:"; echo "$missing"; exit 1; fi
echo "clean install OK ('"$NAMES"')"
'
