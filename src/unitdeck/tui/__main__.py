# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Entry point: ``python -m unitdeck.tui`` or the ``unitdeck-tui`` script."""

from __future__ import annotations

import sys

from unitdeck import __version__
from unitdeck.i18n import set_language
from unitdeck.rootcheck import ensure_not_root


def main() -> None:
    if "--version" in sys.argv[1:]:
        print(f"UnitDeck {__version__}")
        return
    ensure_not_root()
    set_language("system")
    from unitdeck.tui.app import UnitDeckApp

    UnitDeckApp().run()


if __name__ == "__main__":
    main()
