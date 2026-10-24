# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Entry point: ``python -m unitdeck`` or the ``unitdeck`` script."""

import os
import sys

from unitdeck import APP_ID, __version__

ROOT_ERROR = (
    "UnitDeck must not run as root.\n"
    "Run it as a normal user: privileged actions are authorized through polkit."
)


def ensure_not_root() -> None:
    """Exit immediately when running as root. There is no way to bypass this."""
    if os.geteuid() == 0:
        sys.exit(ROOT_ERROR)


def main() -> None:
    if "--version" in sys.argv[1:]:
        print(f"UnitDeck {__version__}")
        return
    ensure_not_root()
    if "--check" in sys.argv[1:]:  # packaging smoke test: Qt and its plugins load, nothing shown
        import PyQt6.QtDBus  # noqa: F401
        import PyQt6.QtNetwork  # noqa: F401
        from PyQt6.QtWidgets import QApplication

        QApplication(sys.argv)
        print(f"UnitDeck {__version__}: Qt ok")
        return
    # Qt is imported only after the root check, so the check runs even if Qt is broken.
    from PyQt6.QtWidgets import QApplication

    from unitdeck.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("UnitDeck")
    app.setOrganizationName("UnitDeck")  # QSettings -> ~/.config/UnitDeck/UnitDeck.conf
    app.setApplicationVersion(__version__)
    app.setDesktopFileName(APP_ID)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
