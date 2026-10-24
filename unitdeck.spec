# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
# PyInstaller spec: one-directory bundle in dist/unitdeck, packaged by packaging/build-deb.sh.
# The privileged helper is NOT bundled: it stays a plain Python script (see helper/).

import re

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

# Libraries that must come from the system, never from the bundle: the GTK stack linked by
# the platform theme plugin (a bundled copy would clash with the host's GTK), OpenSSL and
# Kerberos (security updates must come from apt) and the compression and X/Wayland libraries
# every Ubuntu has. Which of them PyInstaller finds depends on the build host, so they are
# filtered out explicitly; the package declares them in Depends/Recommends.
SYSTEM_LIBS = (
    "gtk-3 gdk-3 gdk_pixbuf-2.0 cairo cairo-gobject pango-1.0 pangocairo-1.0 pangoft2-1.0 "
    "harfbuzz atk-1.0 atk-bridge-2.0 atspi epoxy fribidi thai datrie graphite2 pixman-1 "
    "gmodule-2.0 gio-2.0 gobject-2.0 glib-2.0 gthread-2.0 mount blkid selinux pcre2-8 "
    "X11 X11-xcb Xi Xrandr Xfixes Xcursor Xinerama Xcomposite Xdamage Xext Xrender xkbcommon "
    "xkbcommon-x11 wayland-client wayland-cursor wayland-egl fontconfig freetype dbus-1 "
    "ssl crypto gssapi_krb5 krb5 k5crypto krb5support keyutils com_err "
    "expat ffi z bz2 lzma zstd"
).split()
SYSTEM_LIB = re.compile(r"^lib(?:" + "|".join(re.escape(n) for n in SYSTEM_LIBS) + r")\.so(?:\.\d+)*$")

a = Analysis(
    ["src/unitdeck/__main__.py"],
    pathex=["src"],
    datas=collect_data_files("unitdeck", includes=["templates/*.service"]) + copy_metadata("unitdeck"),
    hiddenimports=["pkgutil"],  # imported by PyQt6/__init__.py, missed by the analysis on 3.12
    excludes=["tkinter", "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.QtMultimedia", "PyQt6.QtWebEngineCore"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="unitdeck",
    console=False,
    strip=True,
    upx=False,
)
binaries = [entry for entry in a.binaries if not SYSTEM_LIB.match(entry[0].rsplit("/", 1)[-1])]
coll = COLLECT(exe, binaries, a.datas, strip=True, upx=False, name="unitdeck")
