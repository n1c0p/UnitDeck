# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
# PyInstaller spec of the terminal interface: one-directory bundle in dist/unitdeck-tui, no Qt.
# The system-library filter is the one of unitdeck.spec.

import re
import runpy

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

SYSTEM_LIB = runpy.run_path("unitdeck.spec.libs")["SYSTEM_LIB"]

a = Analysis(
    ["src/unitdeck/tui/__main__.py"],
    pathex=["src"],
    datas=collect_data_files("unitdeck", includes=["templates/*.service"]) + copy_metadata("unitdeck"),
    hiddenimports=["pkgutil"],
    excludes=["tkinter", "PyQt6", "unitdeck.gui", "unitdeck.model", "unitdeck.updater"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, exclude_binaries=True, name="unitdeck-tui", console=True, strip=True, upx=False)
binaries = [entry for entry in a.binaries if not SYSTEM_LIB.match(entry[0].rsplit("/", 1)[-1])]
coll = COLLECT(exe, binaries, a.datas, strip=True, upx=False, name="unitdeck-tui")
