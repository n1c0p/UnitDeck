#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
#
# Install the given .deb in a clean Ubuntu 24.04 container (Docker) and run the smoke checks
# as a normal user: --version, --check (Qt loads offscreen), the helper refuses a bad name.
set -eu
DEB="$(realpath "$1")"
docker run --rm -v "$(dirname "$DEB"):/pkg:ro" ubuntu:24.04 sh -c '
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -y -qq --no-install-recommends /pkg/'"$(basename "$DEB")"' >/dev/null
runuser -u ubuntu -- unitdeck --version
QT_QPA_PLATFORM=offscreen runuser -u ubuntu -- unitdeck --check
if /usr/libexec/unitdeck/unitdeck-helper write-unit ../x.service </dev/null 2>/dev/null; then
    echo "helper accepted a bad unit name"; exit 1
fi
# Every bundled library must resolve, except optional plugins Qt loads only when their
# desktop (GTK) libraries are present: those are Recommends, not Depends.
missing="$(find /opt/unitdeck -name "*.so*" -not -path "*/platformthemes/*" | while read -r lib; do
    ldd "$lib" 2>/dev/null | grep "not found" | sed "s|^|$lib: |"; done | sort -u || true)"
if [ -n "$missing" ]; then echo "unresolved libraries:"; echo "$missing"; exit 1; fi
echo "clean install OK"
'
