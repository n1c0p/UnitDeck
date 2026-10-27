# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
# PyInstaller spec: one-directory bundle in dist/unitdeck, packaged by packaging/build-deb.sh.
# The privileged helper is NOT bundled: it stays a plain Python script (see helper/).

import runpy

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

SYSTEM_LIB = runpy.run_path("unitdeck.spec.libs")["SYSTEM_LIB"]

a = Analysis(
    ["src/unitdeck/__main__.py"],
    pathex=["src"],
    datas=collect_data_files("unitdeck", includes=["templates/*.service"]) + copy_metadata("unitdeck"),
    hiddenimports=["pkgutil"],  # imported by PyQt6/__init__.py, missed by the analysis on 3.12
    excludes=["tkinter", "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.QtMultimedia", "PyQt6.QtWebEngineCore", "textual", "dbus_fast", "unitdeck.tui"],
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
